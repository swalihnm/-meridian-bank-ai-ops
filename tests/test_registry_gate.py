"""Tests for the promotion gate: targets from METRICS.md and the no-regression rule."""

from __future__ import annotations

from ml.pipelines.registry import gate_decision

GOOD = {"test_accuracy": 0.93, "test_macro_f1": 0.92, "test_ece_calibrated": 0.02}


def test_promotes_when_all_targets_met_and_no_production() -> None:
    assert gate_decision(GOOD, None).promote


def test_refuses_when_accuracy_below_target() -> None:
    decision = gate_decision({**GOOD, "test_accuracy": 0.8935}, None)
    assert not decision.promote
    assert any("test_accuracy" in r for r in decision.reasons)


def test_refuses_when_calibration_is_poor() -> None:
    decision = gate_decision({**GOOD, "test_ece_calibrated": 0.13}, None)
    assert not decision.promote
    assert any("test_ece_calibrated" in r for r in decision.reasons)


def test_refuses_regression_against_production() -> None:
    production = {"test_accuracy": 0.935, "test_macro_f1": 0.92}
    decision = gate_decision({**GOOD, "test_accuracy": 0.925}, production)
    assert not decision.promote
    assert any("regresses" in r for r in decision.reasons)


def test_small_change_within_tolerance_is_allowed() -> None:
    production = {"test_accuracy": 0.9300, "test_macro_f1": 0.9200}
    assert gate_decision({**GOOD, "test_accuracy": 0.9270}, production).promote
