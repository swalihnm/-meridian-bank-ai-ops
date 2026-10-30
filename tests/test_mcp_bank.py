"""MCP tool server tests, run through a real MCP client session (in memory)."""

from __future__ import annotations

import json
from typing import Any

import pytest
from mcp.shared.memory import create_connected_server_and_client_session

from data.generator.generate import GeneratorConfig, generate_bank
from services.mcp_bank.mcp_server import build_server
from services.mcp_bank.server import BankToolServer
from services.mockbank.bank import MockBank


@pytest.fixture
def world() -> tuple[BankToolServer, MockBank]:
    data = generate_bank(
        GeneratorConfig(seed=13, n_customers=400, mean_transactions_per_account=20)
    )
    bank = MockBank.from_frames(data.customers, data.accounts, data.cards, data.transactions)
    return BankToolServer(bank), bank


def _customer_with_card(bank: MockBank) -> str:
    for customer in bank.customers["customer_id"]:
        accounts = bank.accounts.loc[bank.accounts["customer_id"] == customer, "account_id"]
        if any(bank.card_for_account(str(a)) for a in accounts):
            return str(customer)
    raise AssertionError("no customer with a card")


def _payload(result: Any) -> dict[str, Any]:
    text = result.content[0].text
    return json.loads(text) if text.strip().startswith("{") else {"text": text}


@pytest.mark.anyio
async def test_tool_list_has_no_money_movement(world: tuple[BankToolServer, MockBank]) -> None:
    tools, bank = world
    server = build_server(tools, _customer_with_card(bank))
    async with create_connected_server_and_client_session(server._mcp_server) as client:
        names = {t.name for t in (await client.list_tools()).tools}
    banned = ("transfer", "pay", "withdraw", "send", "payout", "wire")
    assert names, "server exposes tools"
    assert not [n for n in names if any(b in n for b in banned)]


@pytest.mark.anyio
async def test_own_account_balance_works(world: tuple[BankToolServer, MockBank]) -> None:
    tools, bank = world
    customer = _customer_with_card(bank)
    account = str(bank.accounts.loc[bank.accounts["customer_id"] == customer, "account_id"].iloc[0])
    server = build_server(tools, customer)
    async with create_connected_server_and_client_session(server._mcp_server) as client:
        result = await client.call_tool("get_balance", {"account_id": account})
    assert not result.isError
    assert _payload(result)["balance_fils"] == bank.get_balance(account)


@pytest.mark.anyio
async def test_other_customers_account_is_refused(world: tuple[BankToolServer, MockBank]) -> None:
    tools, bank = world
    customer = _customer_with_card(bank)
    own = set(bank.accounts.loc[bank.accounts["customer_id"] == customer, "account_id"])
    foreign = str(bank.accounts.loc[~bank.accounts["account_id"].isin(own), "account_id"].iloc[0])
    server = build_server(tools, customer)
    async with create_connected_server_and_client_session(server._mcp_server) as client:
        result = await client.call_tool("get_balance", {"account_id": foreign})
    assert result.isError


@pytest.mark.anyio
async def test_freeze_is_two_step_and_only_own_card(world: tuple[BankToolServer, MockBank]) -> None:
    tools, bank = world
    customer = _customer_with_card(bank)
    own_accounts = set(bank.accounts.loc[bank.accounts["customer_id"] == customer, "account_id"])
    own_card = next(
        str(bank.card_for_account(str(a))) for a in own_accounts if bank.card_for_account(str(a))
    )
    foreign_card = str(
        bank.cards.loc[~bank.cards["account_id"].isin(own_accounts), "card_id"].iloc[0]
    )
    server = build_server(tools, customer)
    async with create_connected_server_and_client_session(server._mcp_server) as client:
        refused = await client.call_tool(
            "propose_write", {"tool": "freeze_card", "args": {"card_id": foreign_card}}
        )
        assert refused.isError

        proposed = await client.call_tool(
            "propose_write", {"tool": "freeze_card", "args": {"card_id": own_card}}
        )
        assert not proposed.isError
        assert bank.get_card(own_card)["status"] != "frozen"  # not executed yet

        confirmed = await client.call_tool("confirm_write", {"token": _payload(proposed)["token"]})
        assert not confirmed.isError
    assert bank.get_card(own_card)["status"] == "frozen"


@pytest.mark.anyio
async def test_large_dispute_needs_approval_through_mcp(
    world: tuple[BankToolServer, MockBank],
) -> None:
    tools, bank = world
    customer = _customer_with_card(bank)
    own = set(bank.accounts.loc[bank.accounts["customer_id"] == customer, "account_id"])
    big = bank.transactions.loc[
        bank.transactions["account_id"].isin(own)
        & (bank.transactions["amount_fils"].abs() >= 100_000),
        "txn_id",
    ]
    if big.empty:
        pytest.skip("no large transaction for this customer in this seed")
    server = build_server(tools, customer)
    async with create_connected_server_and_client_session(server._mcp_server) as client:
        proposed = await client.call_tool(
            "propose_write",
            {"tool": "open_dispute", "args": {"txn_id": str(big.iloc[0]), "reason": "not mine"}},
        )
        confirmed = await client.call_tool("confirm_write", {"token": _payload(proposed)["token"]})
    assert confirmed.isError
