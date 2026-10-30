"""Classification metrics, calibration and temperature scaling for the intent models.

Plain numpy so the maths is easy to check. Expected calibration error (ECE) uses equal-width
confidence bins; the bin count is always reported next to the number.
"""

from __future__ import annotations

import numpy as np
import numpy.typing as npt
from scipy.optimize import minimize_scalar
from scipy.special import softmax

FloatArray = npt.NDArray[np.float64]
IntArray = npt.NDArray[np.int64]


def accuracy(y_true: IntArray, y_pred: IntArray) -> float:
    return float(np.mean(y_true == y_pred))


def macro_f1(y_true: IntArray, y_pred: IntArray, n_classes: int) -> float:
    """Unweighted mean of per-class F1. Classes with no true and no predicted items score 0."""
    scores = []
    for c in range(n_classes):
        tp = np.sum((y_pred == c) & (y_true == c))
        fp = np.sum((y_pred == c) & (y_true != c))
        fn = np.sum((y_pred != c) & (y_true == c))
        denom = 2 * tp + fp + fn
        scores.append(0.0 if denom == 0 else float(2 * tp / denom))
    return float(np.mean(scores))


def expected_calibration_error(probs: FloatArray, y_true: IntArray, n_bins: int = 15) -> float:
    """ECE with equal-width confidence bins over [0, 1]."""
    confidence = probs.max(axis=1)
    correct = (probs.argmax(axis=1) == y_true).astype(np.float64)
    edges = np.linspace(0.0, 1.0, n_bins + 1)
    ece = 0.0
    for low, high in zip(edges[:-1], edges[1:], strict=True):
        in_bin = (confidence > low) & (confidence <= high)
        if in_bin.any():
            gap = abs(correct[in_bin].mean() - confidence[in_bin].mean())
            ece += in_bin.mean() * gap
    return float(ece)


def fit_temperature(logits: FloatArray, y_true: IntArray) -> float:
    """Find T > 0 that minimises the NLL of softmax(logits / T) on validation data."""

    def nll(log_t: float) -> float:
        probs = softmax(logits / np.exp(log_t), axis=1)
        picked = np.clip(probs[np.arange(len(y_true)), y_true], 1e-12, 1.0)
        return float(-np.mean(np.log(picked)))

    result = minimize_scalar(nll, bounds=(-3.0, 3.0), method="bounded")
    return float(np.exp(result.x))
