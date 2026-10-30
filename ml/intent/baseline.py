"""Week 2 baseline: TF-IDF features and logistic regression on Banking77.

Run with `make baseline`. Logs parameters and test metrics to MLflow (local ./mlruns, gitignored).
"""

from __future__ import annotations

import mlflow
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline

from ml.intent.banking77 import load_banking77
from ml.intent.metrics import accuracy, macro_f1

EXPERIMENT = "meridian-intent"


def run_baseline(seed: int = 42) -> dict[str, float]:
    splits = load_banking77(seed=seed)
    n_classes = len(splits.label_names)
    model = make_pipeline(
        TfidfVectorizer(ngram_range=(1, 2), sublinear_tf=True, min_df=1),
        LogisticRegression(max_iter=2000, C=10.0, random_state=seed),
    )
    model.fit(splits.train_text, splits.train_label)
    pred = np.asarray(model.predict(splits.test_text), dtype=np.int64)
    metrics = {
        "test_accuracy": accuracy(splits.test_label, pred),
        "test_macro_f1": macro_f1(splits.test_label, pred, n_classes),
    }

    mlflow.set_experiment(EXPERIMENT)
    with mlflow.start_run(run_name="tfidf-logreg-baseline"):
        mlflow.log_params({"model": "tfidf+logreg", "ngram_range": "1-2", "C": 10.0, "seed": seed})
        mlflow.log_metrics(metrics)
    return metrics


if __name__ == "__main__":
    for name, value in run_baseline().items():
        print(f"{name}: {value:.4f}")
