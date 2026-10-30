"""Generate the synthetic Meridian Bank dataset.

Money is stored as integer minor units (fils for AED) to avoid float rounding.
No card numbers, emails or IDs are real. Card numbers are never generated at all:
cards carry only a fictional last-4 digit string.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

MERCHANT_CATEGORIES = (
    "groceries",
    "dining",
    "fuel",
    "travel",
    "online_retail",
    "utilities",
    "atm",
    "transfer_out",
    "salary",
)
CATEGORY_RANGE_FILS: dict[str, tuple[int, int]] = {
    "groceries": (2_000, 40_000),
    "dining": (2_500, 25_000),
    "fuel": (4_000, 25_000),
    "travel": (10_000, 150_000),
    "online_retail": (1_000, 60_000),
    "utilities": (5_000, 40_000),
    "atm": (10_000, 100_000),
    "transfer_out": (5_000, 200_000),
    "salary": (800_000, 2_000_000),
}
CHANNELS = ("app", "email", "chat", "complaint")
LANGUAGES = ("en", "ar")
COUNTRIES = ("AE", "SA")


@dataclass(frozen=True)
class GeneratorConfig:
    """Size and seed of one synthetic dataset.

    Defaults are small; `make data` uses a larger preset.
    """

    seed: int = 42
    n_customers: int = 1_000
    start: str = "2025-01-01"
    days: int = 365
    mean_transactions_per_account: int = 60


@dataclass(frozen=True)
class SyntheticBank:
    customers: pd.DataFrame
    accounts: pd.DataFrame
    cards: pd.DataFrame
    transactions: pd.DataFrame


def generate_bank(config: GeneratorConfig) -> SyntheticBank:
    rng = np.random.default_rng(config.seed)
    customers = _customers(config, rng)
    accounts = _accounts(customers, rng)
    cards = _cards(accounts, rng)
    transactions = _transactions(config, accounts, rng)
    balances = transactions.groupby("account_id")["amount_fils"].sum()
    accounts["balance_fils"] = accounts["opening_fils"] + accounts["account_id"].map(
        balances
    ).fillna(0).astype("int64")
    return SyntheticBank(customers, accounts, cards, transactions)


def _customers(config: GeneratorConfig, rng: np.random.Generator) -> pd.DataFrame:
    n = config.n_customers
    created = pd.Timestamp(config.start) - pd.to_timedelta(rng.integers(30, 3_000, n), unit="D")
    return pd.DataFrame(
        {
            "customer_id": [f"C{i:07d}" for i in range(1, n + 1)],
            "country": rng.choice(COUNTRIES, size=n, p=[0.7, 0.3]),
            "language": rng.choice(LANGUAGES, size=n, p=[0.6, 0.4]),
            "segment": rng.choice(["mass", "affluent", "business"], size=n, p=[0.8, 0.15, 0.05]),
            "created_at": created,
            "verified": rng.random(n) < 0.9,
        }
    )


def _accounts(customers: pd.DataFrame, rng: np.random.Generator) -> pd.DataFrame:
    counts = rng.integers(1, 3, size=len(customers))
    owner = np.repeat(customers["customer_id"].to_numpy(), counts)
    n = len(owner)
    return pd.DataFrame(
        {
            "account_id": [f"A{i:08d}" for i in range(1, n + 1)],
            "customer_id": owner,
            "account_type": rng.choice(["current", "savings"], size=n, p=[0.75, 0.25]),
            "currency": "AED",
            "opening_fils": rng.integers(50_000, 2_000_000, size=n),
        }
    )


def _cards(accounts: pd.DataFrame, rng: np.random.Generator) -> pd.DataFrame:
    has_card = rng.random(len(accounts)) < 0.8
    held = accounts.loc[has_card, ["account_id"]].reset_index(drop=True)
    n = len(held)
    return pd.DataFrame(
        {
            "card_id": [f"K{i:08d}" for i in range(1, n + 1)],
            "account_id": held["account_id"],
            "last4": [f"{x:04d}" for x in rng.integers(0, 10_000, size=n)],
            "status": rng.choice(["active", "frozen"], size=n, p=[0.95, 0.05]),
        }
    )


def _transactions(
    config: GeneratorConfig, accounts: pd.DataFrame, rng: np.random.Generator
) -> pd.DataFrame:
    counts = rng.poisson(config.mean_transactions_per_account, size=len(accounts))
    account_ids = np.repeat(accounts["account_id"].to_numpy(), counts)
    n = len(account_ids)
    categories = rng.choice(MERCHANT_CATEGORIES, size=n)
    lows = np.array([CATEGORY_RANGE_FILS[c][0] for c in categories])
    highs = np.array([CATEGORY_RANGE_FILS[c][1] for c in categories])
    magnitude = rng.integers(lows, highs + 1)
    is_income = categories == "salary"
    start = pd.Timestamp(config.start)
    ts = start + pd.to_timedelta(rng.integers(0, config.days * 24 * 60, n), unit="m")
    return pd.DataFrame(
        {
            "txn_id": [f"T{i:010d}" for i in range(1, n + 1)],
            "account_id": account_ids,
            "booked_at": ts,
            "category": categories,
            "amount_fils": np.where(is_income, magnitude, -magnitude).astype("int64"),
        }
    ).sort_values(["account_id", "booked_at"], ignore_index=True)


def write_parquet(bank: SyntheticBank, out_dir: Path) -> dict[str, Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    paths = {
        "customers": out_dir / "customers.parquet",
        "accounts": out_dir / "accounts.parquet",
        "cards": out_dir / "cards.parquet",
        "transactions": out_dir / "transactions.parquet",
    }
    bank.customers.to_parquet(paths["customers"], index=False)
    bank.accounts.to_parquet(paths["accounts"], index=False)
    bank.cards.to_parquet(paths["cards"], index=False)
    bank.transactions.to_parquet(paths["transactions"], index=False)
    return paths


if __name__ == "__main__":
    import argparse

    from data.generator.validate import validate_bank

    parser = argparse.ArgumentParser(description="Generate synthetic Meridian bank data.")
    parser.add_argument("--customers", type=int, default=100_000)
    parser.add_argument("--txns-per-account", type=int, default=20)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--out", type=Path, default=Path("data/processed"))
    args = parser.parse_args()
    cfg = GeneratorConfig(
        seed=args.seed,
        n_customers=args.customers,
        mean_transactions_per_account=args.txns_per_account,
    )
    bank = generate_bank(cfg)
    validate_bank(bank)
    for name, path in write_parquet(bank, args.out).items():
        print(f"{name}: {path}")
