"""Paired comparison of the three intent models on the official Banking77 test split (Week 3).

Models: TF-IDF + logistic regression (baseline), DistilBERT fine-tuned (checkpoint), Keras dense
network on TF-IDF (predictions saved by ml/intent/keras_baseline.py, run in .venv-keras).

Each pair is compared with an exact McNemar test on the examples where the two models disagree.
Writes ml/intent/results/paired_compare.json.

Run in the main environment after keras_baseline: python -m ml.intent.paired_compare
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import torch
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from transformers import AutoModelForSequenceClassification, AutoTokenizer

from ml.intent.banking77 import load_banking77
from ml.intent.finetune import ARTIFACT_DIR, MODEL_ID, TextDataset
from ml.intent.metrics import accuracy
from services.experiments.stats import mcnemar_exact, wilson_interval

RESULTS = Path("ml/intent/results/paired_compare.json")
KERAS_PRED = Path("ml/intent/results/keras_test_pred.npy")
SEED = 42


def tfidf_predictions(splits) -> np.ndarray:  # type: ignore[no-untyped-def]
    model = make_pipeline(
        TfidfVectorizer(ngram_range=(1, 2), sublinear_tf=True, min_df=1),
        LogisticRegression(max_iter=2000, C=10.0, random_state=SEED),
    )
    model.fit(splits.train_text, splits.train_label)
    return np.asarray(model.predict(splits.test_text), dtype=np.int64)


@torch.no_grad()
def distilbert_predictions(splits, checkpoint: Path) -> np.ndarray:  # type: ignore[no-untyped-def]
    tokenizer = AutoTokenizer.from_pretrained(MODEL_ID)
    model = AutoModelForSequenceClassification.from_pretrained(
        MODEL_ID, num_labels=len(splits.label_names)
    )
    state = torch.load(checkpoint, map_location="cpu")
    model.load_state_dict(state)
    model.eval()
    dataset = TextDataset(splits.test_text, splits.test_label, tokenizer, 64)
    preds = []
    for start in range(0, len(dataset), 64):
        batch = [dataset[i] for i in range(start, min(start + 64, len(dataset)))]
        out = model(
            input_ids=torch.stack([b["input_ids"] for b in batch]),
            attention_mask=torch.stack([b["attention_mask"] for b in batch]),
        )
        preds.append(out.logits.argmax(dim=1).numpy())
    return np.concatenate(preds).astype(np.int64)


def pair(
    name_a: str, pa: np.ndarray, name_b: str, pb: np.ndarray, y: np.ndarray
) -> dict[str, object]:
    ca = pa == y
    cb = pb == y
    a_only = int(np.sum(ca & ~cb))
    b_only = int(np.sum(cb & ~ca))
    return {
        "pair": f"{name_a} vs {name_b}",
        f"{name_a}_only_correct": a_only,
        f"{name_b}_only_correct": b_only,
        "mcnemar_p": mcnemar_exact(a_only, b_only),
    }


def main(checkpoint: Path = ARTIFACT_DIR / "distilbert_intent.pt") -> None:
    splits = load_banking77(seed=SEED)
    y = splits.test_label
    preds = {
        "tfidf_logreg": tfidf_predictions(splits),
        "distilbert": distilbert_predictions(splits, checkpoint),
        "keras_tfidf": np.load(KERAS_PRED).astype(np.int64),
    }
    n = len(y)
    summary = {
        name: {
            "accuracy": accuracy(y, p),
            "accuracy_ci95": wilson_interval(int(np.sum(p == y)), n),
        }
        for name, p in preds.items()
    }
    comparisons = [
        pair("keras_tfidf", preds["keras_tfidf"], "distilbert", preds["distilbert"], y),
        pair("keras_tfidf", preds["keras_tfidf"], "tfidf_logreg", preds["tfidf_logreg"], y),
        pair("distilbert", preds["distilbert"], "tfidf_logreg", preds["tfidf_logreg"], y),
    ]
    result = {
        "n_test": n,
        "checkpoint": str(checkpoint),
        "models": summary,
        "paired_tests": comparisons,
    }
    RESULTS.parent.mkdir(parents=True, exist_ok=True)
    RESULTS.write_text(json.dumps(result, indent=2, default=float), encoding="utf-8")
    print(json.dumps(result, indent=2, default=float))


if __name__ == "__main__":
    import sys

    main(Path(sys.argv[1]) if len(sys.argv) > 1 else ARTIFACT_DIR / "distilbert_intent.pt")
