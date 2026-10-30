"""Export customer risk features to Parquet for the Feast feature store (Week 7).

The same `build_features` function used for training writes the batch file. Feast then serves these
values online. `ml/pipelines/feast_parity.py` checks that the online values match the batch values.

Run: python -m ml.pipelines.export_features
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from data.generator.generate import GeneratorConfig, generate_bank
from ml.risk.model import FEATURES, build_features

OUT_DIR = Path("data/processed/feast")
EVENT_TIME = pd.Timestamp("2025-12-31T00:00:00", tz="UTC")


def export(seed: int = 42, n_customers: int = 5_000) -> Path:
    bank = generate_bank(
        GeneratorConfig(seed=seed, n_customers=n_customers, mean_transactions_per_account=20)
    )
    features = build_features(bank)
    frame = features[FEATURES].reset_index().rename(columns={"index": "customer_id"})
    frame.insert(1, "event_timestamp", EVENT_TIME)
    for column in ("n_accounts", "n_txn"):
        frame[column] = frame[column].astype("int64")
    for column in FEATURES:
        if column not in ("n_accounts", "n_txn"):
            frame[column] = frame[column].astype("float32")
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    path = OUT_DIR / "customer_risk_features.parquet"
    frame.to_parquet(path, index=False)
    return path


if __name__ == "__main__":
    print(export())
