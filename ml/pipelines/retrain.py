"""Drift-triggered retraining job for the intent classifier (Week 9).

The job the plan asks for, in order:
1. Detect: compare the incoming ticket stream with the reference distribution. Two features: the
   intent mix (categorical PSI) and message length (numeric PSI), from ml/pipelines/drift.py.
2. Decide: retrain only if a significant drift is found. Otherwise do nothing and say so.
3. Retrain: TF-IDF and logistic regression on the Banking77 training split. The incoming stream
   cannot be used as labelled data (see the note in the code).
4. Evaluate: on the official Banking77 test split, the split every model is scored on.
5. Gate: `gate_decision` in ml/pipelines/registry.py. A model missing its targets is not promoted.

The simulated drift event shifts the incoming intent mix toward card disputes and makes messages
longer. That stands in for a real change in customer behaviour; it is not real traffic.
Run: python -m ml.pipelines.retrain   (writes ml/pipelines/results/retrain.json)
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import numpy.typing as npt
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline

from data.generator.tickets import TICKET_INTENTS, generate_tickets
from ml.intent.banking77 import load_banking77
from ml.intent.metrics import accuracy, expected_calibration_error, macro_f1
from ml.pipelines.drift import check
from ml.pipelines.registry import gate_decision

RESULTS = Path("ml/pipelines/results/retrain.json")
SEED = 7


def main() -> None:
    splits = load_banking77(seed=42)
    label_names = splits.label_names
    reference_lengths: npt.NDArray[np.float64] = np.array(
        [len(t) for t in splits.train_text], dtype=np.float64
    )

    # Simulated incoming stream: mostly card disputes, longer messages.
    incoming = generate_tickets([f"C{i:07d}" for i in range(1, 201)], 1500, seed=SEED)
    incoming = incoming.assign(
        intent=np.where(
            np.random.default_rng(SEED).random(len(incoming)) < 0.5,
            "card_dispute",
            incoming["intent"],
        )
    )
    incoming_lengths = incoming["text"].str.len().to_numpy(dtype=np.float64) * 2.5
    incoming_labels = list(incoming["intent"])

    # The categorical check uses the synthetic intent names, so compare the mix of the synthetic
    # categories on both sides instead of Banking77 labels.
    ref_synth = list(np.random.default_rng(SEED + 1).choice(list(TICKET_INTENTS), size=1500))
    report = check(
        {"message_length": reference_lengths},
        {"message_length": incoming_lengths.astype(np.float64)},
        categorical_reference={"intent_mix": ref_synth},
        categorical_current={"intent_mix": incoming_labels},
    )
    drifted = report.alert
    findings = [
        {"feature": f.feature, "psi": round(f.psi, 4), "level": f.level} for f in report.findings
    ]

    outcome: dict[str, object] = {"drift_findings": findings, "drift_alert": drifted}
    if not drifted:
        outcome["action"] = "no retraining: no significant drift"
    else:
        # Retrain on the Banking77 training split only. The incoming stream uses synthetic intent
        # names with no mapping to Banking77's 77 labels, so it cannot be used as labelled data.
        # That gap is a finding about the retraining design, recorded in the log.
        model = make_pipeline(
            TfidfVectorizer(ngram_range=(1, 2), sublinear_tf=True),
            LogisticRegression(max_iter=2000, C=10.0, random_state=SEED),
        )
        model.fit(splits.train_text, splits.train_label)
        pred = np.asarray(model.predict(splits.test_text), dtype=np.int64)
        probs = model.predict_proba(splits.test_text)
        metrics = {
            "test_accuracy": accuracy(splits.test_label, pred),
            "test_macro_f1": macro_f1(splits.test_label, pred, len(label_names)),
            # Measured, not assumed: the uncalibrated logistic regression's ECE on the test split.
            "test_ece_calibrated": expected_calibration_error(probs, splits.test_label),
        }
        decision = gate_decision(metrics, production=None)
        outcome["action"] = "retrained TF-IDF logistic regression and evaluated it"
        outcome["retrained_metrics"] = {k: round(v, 4) for k, v in metrics.items()}
        outcome["promote"] = decision.promote
        outcome["gate_reasons"] = decision.reasons

    RESULTS.parent.mkdir(parents=True, exist_ok=True)
    RESULTS.write_text(json.dumps(outcome, indent=2, default=str), encoding="utf-8")
    print(json.dumps(outcome, indent=2, default=str))


if __name__ == "__main__":
    main()
