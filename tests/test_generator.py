"""Tests for the seeded synthetic bank generator and its validation."""

from __future__ import annotations

import hashlib

import pandas as pd
import pytest

from data.generator.generate import GeneratorConfig, generate_bank
from data.generator.tickets import TICKET_INTENTS, generate_tickets
from data.generator.validate import validate_bank

SMALL = GeneratorConfig(seed=7, n_customers=300, mean_transactions_per_account=20)


def _digest(frame: pd.DataFrame) -> str:
    return hashlib.sha256(
        pd.util.hash_pandas_object(frame, index=False).to_numpy().tobytes()
    ).hexdigest()


def test_same_seed_gives_identical_output() -> None:
    a = generate_bank(SMALL)
    b = generate_bank(SMALL)
    for name in ("customers", "accounts", "cards", "transactions"):
        assert _digest(getattr(a, name)) == _digest(getattr(b, name)), name


def test_different_seed_changes_output() -> None:
    a = generate_bank(SMALL)
    b = generate_bank(GeneratorConfig(seed=8, n_customers=300, mean_transactions_per_account=20))
    assert _digest(a.transactions) != _digest(b.transactions)


def test_generated_bank_passes_validation() -> None:
    validate_bank(generate_bank(SMALL))


def test_balance_equals_opening_plus_transactions() -> None:
    bank = generate_bank(SMALL)
    net = bank.transactions.groupby("account_id")["amount_fils"].sum()
    for row in bank.accounts.to_dict("records"):
        expected = int(row["opening_fils"]) + int(net.get(row["account_id"], 0))
        assert row["balance_fils"] == expected


def test_validation_rejects_dangling_account_reference() -> None:
    bank = generate_bank(SMALL)
    bad_accounts = bank.accounts.iloc[1:].reset_index(drop=True)
    broken = bank.__class__(bank.customers, bad_accounts, bank.cards, bank.transactions)
    with pytest.raises(ValueError, match="unknown account"):
        validate_bank(broken)


def test_validation_rejects_positive_debit() -> None:
    bank = generate_bank(SMALL)
    tx = bank.transactions.copy()
    idx = tx.index[tx["category"] != "salary"][0]
    tx.loc[idx, "amount_fils"] = abs(int(tx.loc[idx, "amount_fils"]))
    broken = bank.__class__(bank.customers, bank.accounts, bank.cards, tx)
    with pytest.raises(ValueError):
        validate_bank(broken)


def test_tickets_are_labelled_and_reproducible() -> None:
    ids = [f"C{i:07d}" for i in range(1, 51)]
    a = generate_tickets(ids, n_tickets=400, seed=3)
    b = generate_tickets(ids, n_tickets=400, seed=3)
    assert a.equals(b)
    assert set(a["intent"]) <= set(TICKET_INTENTS)
    assert a["ticket_id"].is_unique
    assert a["text"].str.len().min() > 5
