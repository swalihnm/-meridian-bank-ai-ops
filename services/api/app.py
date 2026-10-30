"""FastAPI gateway for the Meridian assistant (PLAN Section 5, services/api).

Endpoints:
- POST /chat            one customer message; session is identified by the X-Session-Token header
- POST /admin/kill      trip the kill-switch (requires X-Admin-Token)
- POST /admin/resume    reset the kill-switch (requires X-Admin-Token)
- GET  /health          liveness
- GET  /metrics         Prometheus metrics

Secrets come from environment variables and are never stored in code:
- MERIDIAN_ADMIN_TOKEN   required to use /admin routes; if unset, admin routes refuse everything
- MERIDIAN_TRACE         set to 'console' to print OpenTelemetry spans to stdout
- MERIDIAN_DATA_DIR      optional path to the generated Parquet data (default: data/processed)

Authentication is a token per session (a stand-in for JWT). Rate limiting is per session.
"""

from __future__ import annotations

import hmac
import os
import time
import uuid
from collections import defaultdict, deque
from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd
from fastapi import Depends, FastAPI, Header, HTTPException, Request, Response
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import ConsoleSpanExporter, SimpleSpanProcessor
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest
from pydantic import BaseModel, Field

from data.generator.generate import GeneratorConfig, generate_bank
from services.assistant.checkpoint import CheckpointStore
from services.assistant.guardrails import KillSwitch
from services.assistant.orchestrator import Assistant, Session
from services.assistant.rag.chunking import Chunk, load_chunks
from services.assistant.rag.lexical import BM25Index
from services.mcp_bank.server import BankToolServer
from services.mockbank.bank import MockBank, NotFoundError

POLICY_PATH = Path("data/policies/POLICIES.md")
POLICY_AR_PATH = Path("data/policies/POLICIES_AR.md")
RATE_LIMIT_PER_MINUTE = 30

REQUESTS = Counter("meridian_chat_requests_total", "Chat requests", ["route"])
LATENCY = Histogram("meridian_chat_latency_seconds", "Chat latency in seconds")
ERRORS = Counter("meridian_chat_errors_total", "Chat errors")


class ChatIn(BaseModel):
    message: str = Field(min_length=1, max_length=1000)
    card_id: str | None = None
    txn_id: str | None = None


class ChatOut(BaseModel):
    reply: str
    route: str | None
    citations: list[str]


class SessionOut(BaseModel):
    session_token: str
    customer_id: str


@dataclass
class AppState:
    assistant: Assistant
    bank: MockBank
    kill: KillSwitch
    sessions: dict[str, Session] = field(default_factory=dict)
    hits: dict[str, deque[float]] = field(default_factory=lambda: defaultdict(deque))


def _load_bank() -> MockBank:
    data_dir = Path(os.environ.get("MERIDIAN_DATA_DIR", "data/processed"))
    if (data_dir / "transactions.parquet").exists():
        customers = pd.read_parquet(data_dir / "customers.parquet")
        accounts = pd.read_parquet(data_dir / "accounts.parquet")
        cards = pd.read_parquet(data_dir / "cards.parquet")
        transactions = pd.read_parquet(data_dir / "transactions.parquet")
    else:
        synthetic = generate_bank(GeneratorConfig(seed=42, n_customers=2_000))
        customers, accounts, cards, transactions = (
            synthetic.customers,
            synthetic.accounts,
            synthetic.cards,
            synthetic.transactions,
        )
    return MockBank.from_frames(customers, accounts, cards, transactions)


def _first_card(bank: MockBank, customer_id: str) -> str | None:
    """The customer's own card, found through their accounts. Never taken from the client."""
    account_ids = bank.accounts.loc[bank.accounts["customer_id"] == customer_id, "account_id"]
    for account_id in account_ids:
        card = bank.card_for_account(str(account_id))
        if card is not None:
            return card
    return None


def _demo_customer(bank: MockBank) -> tuple[str, str | None]:
    for customer_id in bank.customers["customer_id"]:
        card = _first_card(bank, str(customer_id))
        if card is not None:
            return str(customer_id), card
    return str(bank.customers.iloc[0]["customer_id"]), None


def _customer_account_ids(bank: MockBank, customer_id: str) -> set[str]:
    return {
        str(a) for a in bank.accounts.loc[bank.accounts["customer_id"] == customer_id, "account_id"]
    }


def _assert_owns_card(bank: MockBank, customer_id: str, card_id: str) -> None:
    """Refuse cards that are not on one of the customer's own accounts."""
    try:
        card = bank.get_card(card_id)
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail="card not found") from exc
    if card["account_id"] not in _customer_account_ids(bank, customer_id):
        raise HTTPException(status_code=403, detail="card does not belong to this customer")


def _assert_owns_transaction(bank: MockBank, customer_id: str, txn_id: str) -> None:
    """Refuse transactions that are not on one of the customer's own accounts."""
    try:
        txn = bank.find_transaction(txn_id)
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail="transaction not found") from exc
    if txn["account_id"] not in _customer_account_ids(bank, customer_id):
        raise HTTPException(status_code=403, detail="transaction does not belong to this customer")


def policy_chunks() -> list[Chunk]:
    """English and Arabic policy chunks in one index.

    Checked against English-only on the full English golden set (see docs/LOG.md).
    """
    english = load_chunks(POLICY_PATH, window=2, overlap=1)
    arabic = load_chunks(POLICY_AR_PATH, window=2, overlap=1)
    return english + arabic


def build_state() -> AppState:
    bank = _load_bank()
    index = BM25Index(policy_chunks())
    kill = KillSwitch()
    assistant = Assistant(
        BankToolServer(bank),
        lambda q: index.search(q, k=5),
        CheckpointStore(),
        kill_switch=kill,
    )
    return AppState(assistant=assistant, bank=bank, kill=kill)


def _enable_console_tracing() -> None:
    """Print assistant spans to the console. Set MERIDIAN_TRACE=console to turn it on."""
    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(ConsoleSpanExporter()))
    trace.set_tracer_provider(provider)


def create_app(state_factory: Callable[[], AppState] = build_state) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        if os.environ.get("MERIDIAN_TRACE") == "console":
            _enable_console_tracing()
        app.state.meridian = state_factory()
        yield

    app = FastAPI(title="Meridian assistant API", version="0.1.0", lifespan=lifespan)

    def state(request: Request) -> AppState:
        st: AppState = request.app.state.meridian
        return st

    def session_for(token: str | None, st: AppState) -> Session:
        if not token or token not in st.sessions:
            raise HTTPException(status_code=401, detail="unknown or missing session token")
        return st.sessions[token]

    def rate_limit(token: str, st: AppState) -> None:
        now = time.monotonic()
        window = st.hits[token]
        while window and now - window[0] > 60:
            window.popleft()
        if len(window) >= RATE_LIMIT_PER_MINUTE:
            raise HTTPException(status_code=429, detail="rate limit exceeded")
        window.append(now)

    def require_admin(x_admin_token: str | None = Header(default=None)) -> None:
        expected = os.environ.get("MERIDIAN_ADMIN_TOKEN")
        if not expected or not x_admin_token or not hmac.compare_digest(x_admin_token, expected):
            raise HTTPException(status_code=403, detail="admin token required")

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/metrics")
    def metrics() -> Response:
        return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)

    @app.post("/session", response_model=SessionOut)
    def new_session(request: Request) -> SessionOut:
        st = state(request)
        # Demo login: the first customer who holds a card. A real login would identify the customer.
        customer, card_id = _demo_customer(st.bank)
        token = uuid.uuid4().hex
        st.sessions[token] = Session(
            actor=f"cust-{customer}", customer_id=customer, card_id=card_id
        )
        return SessionOut(session_token=token, customer_id=customer)

    @app.post("/chat", response_model=ChatOut)
    def chat(
        body: ChatIn,
        request: Request,
        x_session_token: str | None = Header(default=None),
    ) -> ChatOut:
        st = state(request)
        session = session_for(x_session_token, st)
        rate_limit(x_session_token or "", st)
        if body.card_id is not None:
            _assert_owns_card(st.bank, session.customer_id, body.card_id)
            session.card_id = body.card_id
        if body.txn_id is not None:
            _assert_owns_transaction(st.bank, session.customer_id, body.txn_id)
            session.txn_id = body.txn_id
        started = time.perf_counter()
        try:
            out = st.assistant.handle(uuid.uuid4().hex, session, body.message)
        except Exception as exc:  # any failure is logged as an error and returned safely
            ERRORS.inc()
            raise HTTPException(status_code=500, detail="assistant error") from exc
        finally:
            LATENCY.observe(time.perf_counter() - started)
        route = str(out.get("route")) if out.get("route") is not None else "unknown"
        REQUESTS.labels(route=route).inc()
        return ChatOut(
            reply=str(out["reply"]),
            route=out.get("route"),
            citations=list(out.get("citations", [])),
        )

    @app.post("/admin/kill", dependencies=[Depends(require_admin)])
    def kill(request: Request, reason: str = "manual") -> dict[str, str]:
        state(request).kill.trip(reason)
        return {"status": "paused", "reason": reason}

    @app.post("/admin/resume", dependencies=[Depends(require_admin)])
    def resume(request: Request) -> dict[str, str]:
        state(request).kill.reset()
        return {"status": "running"}

    return app


app = create_app()
