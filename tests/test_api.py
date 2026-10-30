"""HTTP tests for the assistant gateway: auth, chat flow, rate limit, admin gate and kill-switch."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from data.generator.generate import GeneratorConfig, generate_bank
from services.api import app as api
from services.assistant.checkpoint import CheckpointStore
from services.assistant.guardrails import KillSwitch
from services.assistant.orchestrator import Assistant
from services.assistant.rag.chunking import load_chunks
from services.assistant.rag.lexical import BM25Index
from services.mcp_bank.server import BankToolServer
from services.mockbank.bank import MockBank

ADMIN = "test-admin-token"


def _small_state() -> api.AppState:
    data = generate_bank(GeneratorConfig(seed=9, n_customers=300, mean_transactions_per_account=20))
    bank = MockBank.from_frames(data.customers, data.accounts, data.cards, data.transactions)
    index = BM25Index(load_chunks(Path("data/policies/POLICIES.md"), window=2, overlap=1))
    kill = KillSwitch()
    assistant = Assistant(
        BankToolServer(bank), lambda q: index.search(q, k=5), CheckpointStore(), kill_switch=kill
    )
    return api.AppState(assistant=assistant, bank=bank, kill=kill)


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    monkeypatch.setenv("MERIDIAN_ADMIN_TOKEN", ADMIN)
    application: FastAPI = api.create_app(_small_state)
    with TestClient(application) as c:
        yield c


def _session(client: TestClient) -> dict[str, str]:
    token = client.post("/session").json()["session_token"]
    return {"X-Session-Token": token}


def test_health_and_metrics(client: TestClient) -> None:
    assert client.get("/health").json() == {"status": "ok"}
    assert "meridian_chat_requests_total" in client.get("/metrics").text


def test_chat_requires_a_session(client: TestClient) -> None:
    r = client.post("/chat", json={"message": "What is the fee?"})
    assert r.status_code == 401


def test_policy_question_returns_citation(client: TestClient) -> None:
    headers = _session(client)
    body = client.post(
        "/chat", json={"message": "What is my default daily card spending limit?"}, headers=headers
    ).json()
    assert "POL-012" in body["citations"]


def test_freeze_needs_second_turn(client: TestClient) -> None:
    headers = _session(client)
    first = client.post(
        "/chat", json={"message": "Please freeze my card, I lost it"}, headers=headers
    ).json()
    assert "Please confirm" in first["reply"]
    second = client.post("/chat", json={"message": "yes"}, headers=headers).json()
    assert "Done" in second["reply"] or "could not" in second["reply"]


def test_rate_limit_returns_429(client: TestClient) -> None:
    headers = _session(client)
    codes = [
        client.post("/chat", json={"message": "fee?"}, headers=headers).status_code
        for _ in range(api.RATE_LIMIT_PER_MINUTE + 1)
    ]
    assert codes[-1] == 429


def test_admin_routes_refuse_without_token(client: TestClient) -> None:
    assert client.post("/admin/kill").status_code == 403
    assert client.post("/admin/kill", headers={"X-Admin-Token": "wrong"}).status_code == 403


def test_kill_switch_pauses_chat_until_resumed(client: TestClient) -> None:
    headers = _session(client)
    admin = {"X-Admin-Token": ADMIN}
    assert client.post("/admin/kill?reason=incident", headers=admin).status_code == 200
    paused = client.post("/chat", json={"message": "What is the fee?"}, headers=headers).json()
    assert "paused" in paused["reply"]
    client.post("/admin/resume", headers=admin)
    running = client.post("/chat", json={"message": "What is the fee?"}, headers=headers).json()
    assert "paused" not in running["reply"]


def test_admin_token_unset_refuses_everything(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("MERIDIAN_ADMIN_TOKEN", raising=False)
    with TestClient(api.create_app(_small_state)) as c:
        assert c.post("/admin/kill", headers={"X-Admin-Token": "anything"}).status_code == 403


def test_cannot_act_on_another_customers_card(client: TestClient) -> None:
    headers = _session(client)
    st = client.app.state.meridian  # type: ignore[attr-defined]
    owner = next(iter(st.sessions.values())).customer_id
    own_accounts = set(st.bank.accounts.loc[st.bank.accounts["customer_id"] == owner, "account_id"])
    foreign = st.bank.cards.loc[~st.bank.cards["account_id"].isin(own_accounts), "card_id"].iloc[0]
    r = client.post("/chat", json={"message": "freeze", "card_id": str(foreign)}, headers=headers)
    assert r.status_code == 403


def test_cannot_dispute_another_customers_transaction(client: TestClient) -> None:
    headers = _session(client)
    st = client.app.state.meridian  # type: ignore[attr-defined]
    owner = next(iter(st.sessions.values())).customer_id
    own_accounts = set(st.bank.accounts.loc[st.bank.accounts["customer_id"] == owner, "account_id"])
    foreign = st.bank.transactions.loc[
        ~st.bank.transactions["account_id"].isin(own_accounts), "txn_id"
    ].iloc[0]
    r = client.post("/chat", json={"message": "dispute", "txn_id": str(foreign)}, headers=headers)
    assert r.status_code == 403
