"""Drift tests: PSI behaves as expected and a simulated drift event is detected."""

from __future__ import annotations

import numpy as np
import pytest

from data.generator.generate import GeneratorConfig, generate_bank
from ml.pipelines.drift import categorical_psi, check, classify, psi


def test_identical_samples_have_zero_psi() -> None:
    x = np.linspace(0, 1, 1000)
    assert psi(x, x) == pytest.approx(0.0, abs=1e-9)


def test_shifted_sample_has_large_psi() -> None:
    rng = np.random.default_rng(0)
    ref = rng.normal(0, 1, 5000)
    cur = rng.normal(1.0, 1, 5000)
    assert psi(ref, cur) > 0.25


def test_psi_is_small_for_same_distribution() -> None:
    rng = np.random.default_rng(1)
    ref = rng.normal(0, 1, 5000)
    cur = rng.normal(0, 1, 5000)
    assert psi(ref, cur) < 0.10


def test_bands() -> None:
    assert classify(0.05) == "stable"
    assert classify(0.2) == "moderate"
    assert classify(0.3) == "significant"


def test_categorical_psi_detects_new_category() -> None:
    ref = ["a"] * 50 + ["b"] * 50
    cur = ["a"] * 50 + ["c"] * 50
    assert categorical_psi(ref, cur) > 0.25


def test_simulated_drift_event_raises_alert() -> None:
    """Simulate a real change in transaction amounts and check the monitor fires."""
    base = generate_bank(
        GeneratorConfig(seed=21, n_customers=500, mean_transactions_per_account=20)
    )
    ref_amounts = np.abs(base.transactions["amount_fils"].to_numpy(dtype=np.float64))
    shifted = (
        np.abs(base.transactions["amount_fils"].to_numpy(dtype=np.float64)) * 2.5
    )  # e.g. a pricing or fraud-pattern change
    stable = ref_amounts.copy()

    drifted = check({"amount_fils": ref_amounts}, {"amount_fils": shifted})
    unchanged = check({"amount_fils": ref_amounts}, {"amount_fils": stable})
    assert drifted.alert and drifted.retrain_recommended
    assert not unchanged.alert
