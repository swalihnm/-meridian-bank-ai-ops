"""Schema and integrity checks for the synthetic bank data.

Run as part of `make data`. A failed check raises, so bad data never reaches a model.
"""

from __future__ import annotations

import pandas as pd
import pandera.pandas as pa
from pandera.pandas import Column, DataFrameSchema

from data.generator.generate import CATEGORY_RANGE_FILS, SyntheticBank

CUSTOMERS = DataFrameSchema(
    {
        "customer_id": Column(str, pa.Check.str_matches(r"^C\d{7}$"), unique=True),
        "country": Column(str, pa.Check.isin(["AE", "SA"])),
        "language": Column(str, pa.Check.isin(["en", "ar"])),
        "segment": Column(str, pa.Check.isin(["mass", "affluent", "business"])),
        "created_at": Column("datetime64[ns]"),
        "verified": Column(bool),
    },
    strict=True,
)

ACCOUNTS = DataFrameSchema(
    {
        "account_id": Column(str, pa.Check.str_matches(r"^A\d{8}$"), unique=True),
        "customer_id": Column(str),
        "account_type": Column(str, pa.Check.isin(["current", "savings"])),
        "currency": Column(str, pa.Check.equal_to("AED")),
        "opening_fils": Column("int64", pa.Check.ge(0)),
        "balance_fils": Column("int64"),
    },
    strict=True,
)

CARDS = DataFrameSchema(
    {
        "card_id": Column(str, pa.Check.str_matches(r"^K\d{8}$"), unique=True),
        "account_id": Column(str),
        "last4": Column(str, pa.Check.str_matches(r"^\d{4}$")),
        "status": Column(str, pa.Check.isin(["active", "frozen"])),
    },
    strict=True,
)

TRANSACTIONS = DataFrameSchema(
    {
        "txn_id": Column(str, pa.Check.str_matches(r"^T\d{10}$"), unique=True),
        "account_id": Column(str),
        "booked_at": Column("datetime64[ns]"),
        "category": Column(str, pa.Check.isin(list(CATEGORY_RANGE_FILS))),
        "amount_fils": Column("int64"),
    },
    strict=True,
)


def validate_bank(bank: SyntheticBank) -> None:
    """Raise pandera.errors.SchemaError or ValueError on the first problem found."""
    CUSTOMERS.validate(bank.customers)
    ACCOUNTS.validate(bank.accounts)
    CARDS.validate(bank.cards)
    TRANSACTIONS.validate(bank.transactions)
    _check_references(bank)
    _check_amounts(bank.transactions)


def _check_references(bank: SyntheticBank) -> None:
    if not bank.accounts["customer_id"].isin(bank.customers["customer_id"]).all():
        raise ValueError("account references an unknown customer")
    if not bank.cards["account_id"].isin(bank.accounts["account_id"]).all():
        raise ValueError("card references an unknown account")
    if not bank.transactions["account_id"].isin(bank.accounts["account_id"]).all():
        raise ValueError("transaction references an unknown account")


def _check_amounts(transactions: pd.DataFrame) -> None:
    """Debits are negative, salary is positive, and magnitudes stay in the category range."""
    for category, (low, high) in CATEGORY_RANGE_FILS.items():
        rows = transactions[transactions["category"] == category]["amount_fils"].abs()
        if rows.empty:
            continue
        if rows.min() < low or rows.max() > high:
            raise ValueError(f"amount out of range for category {category}")
    income = transactions["category"] == "salary"
    if (transactions.loc[income, "amount_fils"] <= 0).any():
        raise ValueError("salary must be positive")
    if (transactions.loc[~income, "amount_fils"] >= 0).any():
        raise ValueError("non-salary transactions must be debits")
