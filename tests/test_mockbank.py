"""Tests for the mock core-banking service: reads, writes and the no-money-movement rule."""

from __future__ import annotations

import inspect

import pytest

from data.generator.generate import GeneratorConfig, generate_bank
from services.mockbank.bank import MockBank, NotFoundError, VerificationRequiredError


@pytest.fixture
def bank() -> MockBank:
    data = generate_bank(
        GeneratorConfig(seed=11, n_customers=200, mean_transactions_per_account=15)
    )
    return MockBank.from_frames(data.customers, data.accounts, data.cards, data.transactions)


def test_balance_matches_accounts_table(bank: MockBank) -> None:
    account = bank.accounts.iloc[0]
    assert bank.get_balance(account["account_id"]) == int(account["balance_fils"])


def test_unknown_account_raises(bank: MockBank) -> None:
    with pytest.raises(NotFoundError):
        bank.get_balance("A99999999")


def test_transactions_are_newest_first_and_limited(bank: MockBank) -> None:
    account_id = bank.transactions["account_id"].iloc[0]
    rows = bank.list_transactions(account_id, limit=3)
    assert len(rows) <= 3
    stamps = [str(r["booked_at"]) for r in rows]
    assert stamps == sorted(stamps, reverse=True)


def test_freeze_card_changes_status(bank: MockBank) -> None:
    card_id = str(bank.cards.iloc[0]["card_id"])
    bank.set_card_status(card_id, "frozen")
    assert bank.get_card(card_id)["status"] == "frozen"


def test_unknown_card_status_is_rejected(bank: MockBank) -> None:
    card_id = str(bank.cards.iloc[0]["card_id"])
    with pytest.raises(ValueError):
        bank.set_card_status(card_id, "closed")


def test_dispute_is_recorded_against_transaction(bank: MockBank) -> None:
    txn_id = str(bank.transactions.iloc[0]["txn_id"])
    dispute = bank.open_dispute(txn_id, "not my purchase")
    assert dispute.status == "open"
    assert bank.disputes[dispute.dispute_id].txn_id == txn_id


def test_address_change_needs_verified_customer(bank: MockBank) -> None:
    unverified = bank.customers.loc[~bank.customers["verified"], "customer_id"].iloc[0]
    with pytest.raises(VerificationRequiredError):
        bank.update_address(str(unverified), "1 Example Street")


def test_no_method_moves_money() -> None:
    """Design rule (PLAN Section 5): the bank service exposes no way to transfer or pay out."""
    forbidden = ("transfer", "pay", "withdraw", "send", "payout", "move")
    methods = [name for name, _ in inspect.getmembers(MockBank, inspect.isfunction)]
    offending = [m for m in methods if any(word in m.lower() for word in forbidden)]
    assert offending == []
