"""Parity check: Spark risk features vs the pandas definitions used for training (Week 7).

Computes the features with `build_features` (pandas, training path) on a customer subset of the
processed data, then compares them with the Spark output for the same customers.

Run after `spark_features.py`:  python -m ml.pipelines.spark_parity
Writes ml/eval/results/spark_parity.json. Exits non-zero on mismatch.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

from data.generator.generate import SyntheticBank
from ml.risk.model import FEATURES, build_features

PROCESSED = Path("data/processed")
SPARK_OUT = PROCESSED / "spark" / "customer_risk_features.parquet"
RESULTS = Path("ml/eval/results/spark_parity.json")
SUBSET = 20_000
REL_TOL = 1e-9


def subset_bank() -> SyntheticBank:
    customers = pd.read_parquet(PROCESSED / "customers.parquet")
    keep = set(customers["customer_id"].iloc[:SUBSET])
    customers = customers[customers["customer_id"].isin(keep)]
    accounts = pd.read_parquet(PROCESSED / "accounts.parquet")
    accounts = accounts[accounts["customer_id"].isin(keep)]
    cards = pd.read_parquet(PROCESSED / "cards.parquet")
    cards = cards[cards["account_id"].isin(accounts["account_id"])]
    txns = pd.read_parquet(PROCESSED / "transactions.parquet")
    txns = txns[txns["account_id"].isin(accounts["account_id"])]
    return SyntheticBank(customers, accounts, cards, txns)


def main() -> int:
    pandas_features = build_features(subset_bank())
    spark = pd.read_parquet(SPARK_OUT).set_index("customer_id")
    spark = spark.loc[spark.index.intersection(pandas_features.index)]
    pandas_features = pandas_features.loc[spark.index]

    report: dict[str, int] = {}
    mismatches = 0
    for name in FEATURES:
        want = pandas_features[name].to_numpy(dtype=float)
        got = spark[name].to_numpy(dtype=float)
        bad = int(np.sum(~np.isclose(got, want, rtol=REL_TOL, atol=1e-9)))
        report[name] = bad
        mismatches += bad

    result = {
        "customers_compared": int(len(spark)),
        "features_compared": len(FEATURES),
        "relative_tolerance": REL_TOL,
        "mismatches_per_feature": report,
        "total_mismatches": mismatches,
    }
    RESULTS.parent.mkdir(parents=True, exist_ok=True)
    RESULTS.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps({k: result[k] for k in ("customers_compared", "total_mismatches")}, indent=2))
    return 0 if mismatches == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
