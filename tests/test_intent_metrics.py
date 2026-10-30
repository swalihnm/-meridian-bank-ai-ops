"""Hand-checked tests for the intent metrics: accuracy, macro-F1, ECE and temperature scaling."""

from __future__ import annotations

import numpy as np
import pytest

from ml.intent.metrics import (
    accuracy,
    expected_calibration_error,
    fit_temperature,
    macro_f1,
)


def test_accuracy() -> None:
    y = np.array([0, 1, 2, 2])
    p = np.array([0, 1, 1, 2])
    assert accuracy(y, p) == pytest.approx(0.75)


def test_macro_f1_matches_hand_computation() -> None:
    # class 0: tp=1 fp=0 fn=1 -> F1 = 2/3 ; class 1: tp=1 fp=1 fn=0 -> F1 = 2/3
    y = np.array([0, 0, 1])
    p = np.array([0, 1, 1])
    assert macro_f1(y, p, n_classes=2) == pytest.approx(2 / 3)


def test_macro_f1_penalises_missed_rare_class() -> None:
    y = np.array([0, 0, 0, 0, 1])
    p = np.array([0, 0, 0, 0, 0])
    assert accuracy(y, p) == pytest.approx(0.8)
    assert macro_f1(y, p, n_classes=2) < 0.5


def test_ece_is_zero_for_perfectly_calibrated_certain_predictions() -> None:
    probs = np.array([[1.0, 0.0], [0.0, 1.0]])
    y = np.array([0, 1])
    assert expected_calibration_error(probs, y) == pytest.approx(0.0)


def test_ece_detects_overconfident_wrong_predictions() -> None:
    probs = np.array([[0.99, 0.01], [0.99, 0.01]])
    y = np.array([1, 1])  # always wrong with 99% confidence
    assert expected_calibration_error(probs, y) == pytest.approx(0.99, abs=1e-6)


def test_temperature_softens_overconfident_logits() -> None:
    rng = np.random.default_rng(0)
    y = rng.integers(0, 3, size=500)
    logits = rng.normal(size=(500, 3))
    logits[np.arange(500), y] += 1.0  # mostly right, but logits are too sharp
    logits *= 10.0
    t = fit_temperature(logits, y)
    assert t > 1.0
