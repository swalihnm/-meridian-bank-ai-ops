"""Hand-checked tests for the experiment statistics."""

from __future__ import annotations

import pytest

from services.experiments.stats import (
    assign_variant,
    mcnemar_exact,
    sample_size_per_arm,
    two_proportion_z,
    wilson_interval,
)


def test_assignment_is_stable_and_roughly_balanced() -> None:
    units = [f"u{i}" for i in range(4000)]
    first = [assign_variant(u, "exp-1") for u in units]
    assert first == [assign_variant(u, "exp-1") for u in units]
    share_a = first.count("A") / len(first)
    assert 0.45 < share_a < 0.55


def test_assignment_changes_between_experiments() -> None:
    units = [f"u{i}" for i in range(500)]
    a = [assign_variant(u, "exp-1") for u in units]
    b = [assign_variant(u, "exp-2") for u in units]
    assert a != b


def test_wilson_interval_known_value() -> None:
    low, high = wilson_interval(50, 100)
    assert low == pytest.approx(0.4038, abs=1e-3)
    assert high == pytest.approx(0.5962, abs=1e-3)


def test_wilson_interval_stays_inside_unit_range() -> None:
    low, high = wilson_interval(0, 10)
    assert low == 0.0 and 0 < high < 1


def test_two_proportion_test_known_value() -> None:
    diff, p = two_proportion_z(50, 100, 70, 100)
    assert diff == pytest.approx(0.2)
    # pooled p = 0.6, se = sqrt(0.6 * 0.4 * 0.02) = 0.0693, z = 2.887, two-sided p = 0.0039
    assert p == pytest.approx(0.0039, abs=5e-4)


def test_two_proportion_identical_arms_is_not_significant() -> None:
    _, p = two_proportion_z(30, 100, 30, 100)
    assert p == pytest.approx(1.0)


def test_mcnemar_exact_known_value() -> None:
    # 9 discordant pairs, 2 in one direction and 7 in the other: exact two-sided p = 0.1797
    assert mcnemar_exact(2, 7) == pytest.approx(0.1797, abs=1e-3)


def test_mcnemar_no_discordant_pairs() -> None:
    assert mcnemar_exact(0, 0) == 1.0


def test_sample_size_is_plausible() -> None:
    # Detecting 0.5 -> 0.6 at 80 percent power, alpha 0.05, needs about 385 per arm.
    n = sample_size_per_arm(0.5, 0.10)
    assert 350 < n < 420
