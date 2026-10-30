"""MLflow model registry with a promotion gate (Week 9).

A model version is registered as `staging` automatically. It is promoted to `production` only
when it meets the targets in docs/product/METRICS.md, and does not regress on the current
production version.
Promotion is refused otherwise, and the reasons are printed. A refused promotion is the expected
result for a model that misses its targets.

Tracking store: sqlite (mlflow.db, gitignored). Metrics come from the saved results file.
"""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import mlflow
from mlflow.tracking import MlflowClient

TRACKING_URI = "sqlite:///mlflow.db"
MODEL_NAME = "meridian-intent"
RESULTS = Path("ml/intent/results/finetune.json")

# Targets from docs/product/METRICS.md (T4, T5, T6). Changing these needs a dated note in that file.
TARGETS = {
    "test_accuracy": (">=", 0.92),
    "test_macro_f1": (">=", 0.91),
    "test_ece_calibrated": ("<=", 0.05),
}
REGRESSION_TOLERANCE = 0.005


@dataclass(frozen=True)
class Decision:
    promote: bool
    reasons: list[str]


def gate_decision(metrics: dict[str, float], production: dict[str, float] | None) -> Decision:
    """Pure function: target checks, then no-regression against the current production metrics."""
    reasons: list[str] = []
    for name, (op, bound) in TARGETS.items():
        value = metrics[name]
        ok = value >= bound if op == ">=" else value <= bound
        if not ok:
            reasons.append(f"{name} {value:.4f} does not meet {op} {bound}")
    if production is not None:
        for name in ("test_accuracy", "test_macro_f1"):
            if metrics[name] < production[name] - REGRESSION_TOLERANCE:
                reasons.append(
                    f"{name} {metrics[name]:.4f} regresses on production {production[name]:.4f}"
                )
    return Decision(promote=not reasons, reasons=reasons)


def _client() -> MlflowClient:
    mlflow.set_tracking_uri(TRACKING_URI)
    return MlflowClient()


def _ensure_model(client: MlflowClient) -> None:
    try:
        client.get_registered_model(MODEL_NAME)
    except mlflow.exceptions.MlflowException:
        client.create_registered_model(MODEL_NAME)


def register_staging(metrics: dict[str, Any], checkpoint: Path) -> str:
    """Log the run and its checkpoint, register a version, and point the `staging` alias at it."""
    client = _client()
    _ensure_model(client)
    mlflow.set_experiment("meridian-intent-registry")
    with mlflow.start_run(run_name="registry-intake") as run:
        mlflow.log_metrics({k: float(v) for k, v in metrics.items() if isinstance(v, (int, float))})
        mlflow.log_artifact(str(checkpoint), artifact_path="checkpoint")
        source = f"{run.info.artifact_uri}/checkpoint/{checkpoint.name}"
        version = client.create_model_version(MODEL_NAME, source=source, run_id=run.info.run_id)
    client.set_registered_model_alias(MODEL_NAME, "staging", version.version)
    return str(version.version)


def promote_to_production(version: str) -> Decision:
    client = _client()
    metrics = _metrics_for_version(client, version)
    production = _production_metrics(client)
    decision = gate_decision(metrics, production)
    if decision.promote:
        client.set_registered_model_alias(MODEL_NAME, "production", version)
    return decision


def _metrics_for_version(client: MlflowClient, version: str) -> dict[str, float]:
    mv = client.get_model_version(MODEL_NAME, version)
    run = client.get_run(str(mv.run_id))
    return dict(run.data.metrics)


def _production_metrics(client: MlflowClient) -> dict[str, float] | None:
    try:
        mv = client.get_model_version_by_alias(MODEL_NAME, "production")
    except mlflow.exceptions.MlflowException:
        return None
    return _metrics_for_version(client, str(mv.version))


def main(argv: list[str]) -> int:
    if argv and argv[0] == "register":
        results = json.loads(RESULTS.read_text(encoding="utf-8"))
        version = register_staging(results, Path(results["checkpoint"]))
        print(f"registered version {version} as staging")
        return 0
    if argv and argv[0] == "promote":
        decision = promote_to_production(argv[1])
        if decision.promote:
            print("promoted to production")
            return 0
        for reason in decision.reasons:
            print(f"REFUSED: {reason}")
        return 1
    print("usage: python -m ml.pipelines.registry register | promote <version>")
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
