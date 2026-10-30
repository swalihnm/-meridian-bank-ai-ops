"""In-memory mock core-banking and CRM service.

This stands in for the existing enterprise system. It holds synthetic data and records
every write. It has NO method that moves money out of an account: there is no transfer,
payment or withdrawal call. This is the design rule from docs/PROJECT_PLAN.md Section 5,
and tests enforce it.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

import pandas as pd


class NotFoundError(LookupError):
    """Raised when a customer, account, card or transaction does not exist."""


class VerificationRequiredError(PermissionError):
    """Raised when a write needs a verified customer."""


@dataclass
class Dispute:
    dispute_id: str
    txn_id: str
    account_id: str
    reason: str
    status: str
    opened_at: str


@dataclass
class MockBank:
    customers: pd.DataFrame
    accounts: pd.DataFrame
    cards: pd.DataFrame
    transactions: pd.DataFrame
    cards_status: dict[str, str] = field(default_factory=dict)
    disputes: dict[str, Dispute] = field(default_factory=dict)
    addresses: dict[str, str] = field(default_factory=dict)

    @classmethod
    def from_frames(
        cls,
        customers: pd.DataFrame,
        accounts: pd.DataFrame,
        cards: pd.DataFrame,
        transactions: pd.DataFrame,
    ) -> MockBank:
        status = dict(zip(cards["card_id"], cards["status"], strict=True))
        return cls(customers, accounts, cards, transactions, cards_status=status)

    # ---- reads -------------------------------------------------------------

    def get_customer(self, customer_id: str) -> dict[str, Any]:
        row = self.customers.loc[self.customers["customer_id"] == customer_id]
        if row.empty:
            raise NotFoundError(customer_id)
        record: dict[str, Any] = {str(k): v for k, v in row.iloc[0].to_dict().items()}
        record["verified"] = bool(record["verified"])
        return record

    def get_balance(self, account_id: str) -> int:
        """Balance in fils (1 AED = 100 fils)."""
        row = self.accounts.loc[self.accounts["account_id"] == account_id]
        if row.empty:
            raise NotFoundError(account_id)
        return int(row.iloc[0]["balance_fils"])

    def list_transactions(self, account_id: str, limit: int = 20) -> list[dict[str, object]]:
        if not (self.accounts["account_id"] == account_id).any():
            raise NotFoundError(account_id)
        rows = self.transactions.loc[self.transactions["account_id"] == account_id]
        recent = rows.sort_values("booked_at", ascending=False).head(limit)
        return [
            {
                "txn_id": r["txn_id"],
                "booked_at": pd.Timestamp(r["booked_at"]).isoformat(),
                "category": r["category"],
                "amount_fils": int(r["amount_fils"]),
            }
            for r in recent.to_dict("records")
        ]

    def get_card(self, card_id: str) -> dict[str, str]:
        row = self.cards.loc[self.cards["card_id"] == card_id]
        if row.empty:
            raise NotFoundError(card_id)
        return {
            "card_id": card_id,
            "account_id": str(row.iloc[0]["account_id"]),
            "last4": str(row.iloc[0]["last4"]),
            "status": self.cards_status[card_id],
        }

    def card_for_account(self, account_id: str) -> str | None:
        row = self.cards.loc[self.cards["account_id"] == account_id]
        return None if row.empty else str(row.iloc[0]["card_id"])

    def find_transaction(self, txn_id: str) -> dict[str, Any]:
        row = self.transactions.loc[self.transactions["txn_id"] == txn_id]
        if row.empty:
            raise NotFoundError(txn_id)
        r = row.iloc[0]
        return {
            "txn_id": txn_id,
            "account_id": str(r["account_id"]),
            "amount_fils": int(r["amount_fils"]),
            "category": str(r["category"]),
        }

    # ---- writes (none move money) -------------------------------------------

    def set_card_status(self, card_id: str, status: str) -> None:
        if status not in {"active", "frozen"}:
            raise ValueError(f"unknown card status: {status}")
        if card_id not in self.cards_status:
            raise NotFoundError(card_id)
        self.cards_status[card_id] = status

    def open_dispute(self, txn_id: str, reason: str) -> Dispute:
        txn = self.find_transaction(txn_id)
        dispute = Dispute(
            dispute_id=f"D{uuid.uuid4().hex[:10]}",
            txn_id=txn_id,
            account_id=str(txn["account_id"]),
            reason=reason,
            status="open",
            opened_at=datetime.now(UTC).isoformat(),
        )
        self.disputes[dispute.dispute_id] = dispute
        return dispute

    def update_address(self, customer_id: str, address: str) -> None:
        customer = self.get_customer(customer_id)
        if not customer["verified"]:
            raise VerificationRequiredError(customer_id)
        self.addresses[customer_id] = address
