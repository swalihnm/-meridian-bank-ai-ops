"""Feature parity check for the Feast store (Week 7).

Checks that what serving reads (online store) matches what training read (offline historical)
and the batch Parquet the features came from. Runs in the Feast environment
(.venv-feast), so it does not import the main project package.

Steps: materialise to the online store, sample customers, read both stores, compare every feature.
Writes ml/eval/results/feast_parity.json and exits non-zero on a mismatch.

Run from the project root with the Feast environment:
    .venv-feast\\Scripts\\python.exe -m ml.pipelines.feast_parity
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from feast import FeatureStore

REPO = Path("feature_repo")
BATCH = Path("data/processed/feast/customer_risk_features.parquet")
RESULTS = Path("ml/eval/results/feast_parity.json")
FEATURES = [
    "n_accounts",
    "n_txn",
    "mean_abs_amount",
    "share_online",
    "share_atm",
    "share_travel",
    "share_transfer_out",
    "income_total",
    "segment_affluent",
    "segment_business",
]
REL_TOL = 1e-5
SAMPLE = 300


def main() -> int:
    store = FeatureStore(repo_path=str(REPO))
    batch = pd.read_parquet(BATCH)
    event_time = batch["event_timestamp"].max()
    store.materialize(
        start_date=pd.Timestamp("2025-01-01", tz="UTC").to_pydatetime(),
        end_date=(event_time + pd.Timedelta(days=1)).to_pydatetime(),
    )

    sample = batch.sample(n=min(SAMPLE, len(batch)), random_state=0).reset_index(drop=True)
    entity_rows = [{"customer_id": cid} for cid in sample["customer_id"]]
    feature_refs = [f"customer_risk_features:{name}" for name in FEATURES]

    online = store.get_online_features(features=feature_refs, entity_rows=entity_rows).to_df()
    entity_df = sample[["customer_id", "event_timestamp"]]
    offline = store.get_historical_features(entity_df=entity_df, features=feature_refs).to_df()

    online = online.set_index("customer_id").loc[sample["customer_id"]]
    offline = offline.set_index("customer_id").loc[sample["customer_id"]]
    expected = sample.set_index("customer_id")

    report: dict[str, dict[str, float | int]] = {}
    failed = 0
    for name in FEATURES:
        want = expected[name].to_numpy(dtype=float)
        on = np.asarray(online[name], dtype=float)
        off = np.asarray(offline[name], dtype=float)
        on_bad = int(np.sum(~np.isclose(on, want, rtol=REL_TOL, atol=1e-9)))
        off_bad = int(np.sum(~np.isclose(off, want, rtol=REL_TOL, atol=1e-9)))
        report[name] = {"online_mismatches": on_bad, "offline_mismatches": off_bad}
        failed += on_bad + off_bad

    result = {
        "customers_checked": len(sample),
        "features_checked": len(FEATURES),
        "tolerance_relative": REL_TOL,
        "total_mismatches": failed,
        "per_feature": report,
    }
    RESULTS.parent.mkdir(parents=True, exist_ok=True)
    RESULTS.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps({"total_mismatches": failed, "customers_checked": len(sample)}, indent=2))
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
