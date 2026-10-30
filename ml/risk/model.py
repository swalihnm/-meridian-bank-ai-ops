"""Risk model for dispute propensity (LightGBM), with SHAP explanations and fairness slices.

IMPORTANT: the synthetic dataset has no real dispute outcomes. The label is generated from a
documented, seeded logistic rule (SYNTHETIC_WEIGHTS below) plus noise. A high AUC here shows the
pipeline recovers a signal we put in on purpose. It is a method check, not evidence of
real-world accuracy.
The model card (docs/model-cards/risk.md) says this in full.

Fairness: country and language are NEVER model inputs. They are used only to slice metrics, so gaps
between groups are reported rather than hidden.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import lightgbm as lgb
import numpy as np
import numpy.typing as npt
import pandas as pd
import shap
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import train_test_split

from data.generator.generate import GeneratorConfig, SyntheticBank, generate_bank

RESULTS_PATH = Path("ml/risk/results/risk_model.json")
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

# Rule: logit = intercept + weights . features + N(0, 0.5); label ~ Bernoulli(sigmoid(logit)).
# The intercept is solved so the base rate is TARGET_RATE. The first attempt used weights of
# 3.0 / 2.0 / 1.0, which gave AUC 0.54 (signal too weak for the noise). The weights below are
# the second attempt.
TARGET_RATE = 0.15
SYNTHETIC_WEIGHTS = {
    "share_online": 12.0,
    "share_travel": 12.0,
    "share_atm": 6.0,
    "segment_business": 0.8,
}


def build_features(bank: SyntheticBank) -> pd.DataFrame:
    tx = bank.transactions.copy()
    tx["abs_amount"] = tx["amount_fils"].abs().astype(np.float64)
    tx = tx.merge(bank.accounts[["account_id", "customer_id"]], on="account_id")
    grouped = tx.groupby("customer_id")
    total = grouped.size().rename("n_txn")
    features = pd.DataFrame(
        {
            "n_txn": total,
            "mean_abs_amount": grouped["abs_amount"].mean(),
            "income_total": tx[tx["category"] == "salary"]
            .groupby("customer_id")["amount_fils"]
            .sum(),
        }
    )
    for name, category in [
        ("share_online", "online_retail"),
        ("share_atm", "atm"),
        ("share_travel", "travel"),
        ("share_transfer_out", "transfer_out"),
    ]:
        features[name] = tx[tx["category"] == category].groupby("customer_id").size() / total
    features["n_accounts"] = bank.accounts.groupby("customer_id").size()
    customers = bank.customers.set_index("customer_id")
    features["segment_affluent"] = (customers["segment"] == "affluent").astype(np.float64)
    features["segment_business"] = (customers["segment"] == "business").astype(np.float64)
    features = features.reindex(customers.index).fillna(0.0)
    features["country"] = customers["country"]
    features["language"] = customers["language"]
    return features


def synthetic_label(features: pd.DataFrame, seed: int) -> npt.NDArray[np.int64]:
    linear = sum(
        weight * features[name].to_numpy(dtype=np.float64)
        for name, weight in SYNTHETIC_WEIGHTS.items()
    )
    rng = np.random.default_rng(seed)
    logit_no_intercept = linear + rng.normal(0.0, 0.5, size=len(features))
    intercept = _solve_intercept(logit_no_intercept, TARGET_RATE)
    prob = 1.0 / (1.0 + np.exp(-(logit_no_intercept + intercept)))
    return rng.binomial(1, prob).astype(np.int64)


def _solve_intercept(logit: npt.NDArray[np.float64], target: float) -> float:
    """Bisection for the intercept that gives the target mean probability."""
    low, high = -20.0, 20.0
    for _ in range(100):
        mid = (low + high) / 2
        if (1.0 / (1.0 + np.exp(-(logit + mid)))).mean() < target:
            low = mid
        else:
            high = mid
    return (low + high) / 2


@dataclass(frozen=True)
class RiskRun:
    auc_test: float
    positive_rate: float
    slice_auc: dict[str, dict[str, float]]
    top_shap: list[tuple[str, float]]


def run(seed: int = 42, n_customers: int = 20_000) -> RiskRun:
    bank = generate_bank(
        GeneratorConfig(seed=seed, n_customers=n_customers, mean_transactions_per_account=20)
    )
    frame = build_features(bank)
    y = synthetic_label(frame, seed)
    x = frame[FEATURES]
    x_tr, x_te, y_tr, y_te, meta_tr, meta_te = train_test_split(
        x, y, frame[["country", "language"]], test_size=0.2, random_state=seed, stratify=y
    )
    model = lgb.LGBMClassifier(
        n_estimators=300, learning_rate=0.05, num_leaves=31, random_state=seed, verbose=-1
    )
    model.fit(x_tr, y_tr)
    scores = np.asarray(model.predict_proba(x_te))[:, 1]
    auc = float(roc_auc_score(y_te, scores))

    slice_auc: dict[str, dict[str, float]] = {}
    for column in ("country", "language"):
        per_group: dict[str, float] = {}
        for group in sorted(meta_te[column].unique()):
            mask = (meta_te[column] == group).to_numpy()
            if len(np.unique(y_te[mask])) == 2:
                per_group[str(group)] = float(roc_auc_score(y_te[mask], scores[mask]))
        slice_auc[column] = per_group

    explainer = shap.TreeExplainer(model)
    sample = x_te.iloc[:2000]
    # shap returns a list per class for some model types; the positive class is index 1.
    raw: Any = explainer.shap_values(sample)
    values = np.asarray(raw[1] if isinstance(raw, list) else raw)
    mean_abs = np.abs(values).mean(axis=0)
    ranked = sorted(zip(FEATURES, mean_abs.tolist(), strict=True), key=lambda kv: -kv[1])

    return RiskRun(
        auc_test=auc,
        positive_rate=float(y.mean()),
        slice_auc=slice_auc,
        top_shap=[(name, float(v)) for name, v in ranked[:5]],
    )


if __name__ == "__main__":
    result = run()
    RESULTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    RESULTS_PATH.write_text(
        json.dumps(
            {
                "auc_test": result.auc_test,
                "positive_rate": result.positive_rate,
                "slice_auc": result.slice_auc,
                "top_shap": result.top_shap,
                "label": "SYNTHETIC rule, not real outcomes",
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    print(
        json.dumps({"auc_test": result.auc_test, "positive_rate": result.positive_rate}, indent=2)
    )
    print("slice_auc", result.slice_auc)
    print("top_shap", result.top_shap)
