"""Drift monitoring with the population stability index (PSI) and a simulated drift event.

Bands (common industry convention): PSI < 0.10 stable, 0.10 to 0.25 moderate,
above 0.25 significant.
A significant drift on any monitored feature raises an alert and recommends retraining. The
decision is returned as data so the scheduler and the alerting layer can act on it.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import numpy.typing as npt

EPS = 1e-6
STABLE_BELOW = 0.10
SIGNIFICANT_ABOVE = 0.25


def psi(
    expected: npt.NDArray[np.float64], actual: npt.NDArray[np.float64], bins: int = 10
) -> float:
    """PSI between a reference sample and a current sample, using reference quantile bins."""
    edges = np.quantile(expected, np.linspace(0.0, 1.0, bins + 1))
    edges[0], edges[-1] = -np.inf, np.inf
    exp_counts, _ = np.histogram(expected, bins=edges)
    act_counts, _ = np.histogram(actual, bins=edges)
    exp_pct = np.clip(exp_counts / exp_counts.sum(), EPS, None)
    act_pct = np.clip(act_counts / act_counts.sum(), EPS, None)
    return float(np.sum((act_pct - exp_pct) * np.log(act_pct / exp_pct)))


def categorical_psi(expected: list[str], actual: list[str]) -> float:
    """PSI over category shares. Categories seen only in the current sample count as new mass."""
    cats = sorted(set(expected) | set(actual))
    exp_total, act_total = len(expected), len(actual)
    total = 0.0
    for cat in cats:
        e = max(expected.count(cat) / exp_total, EPS)
        a = max(actual.count(cat) / act_total, EPS)
        total += (a - e) * np.log(a / e)
    return float(total)


@dataclass(frozen=True)
class DriftFinding:
    feature: str
    psi: float
    level: str


@dataclass(frozen=True)
class DriftReport:
    findings: list[DriftFinding]

    @property
    def alert(self) -> bool:
        return any(f.level == "significant" for f in self.findings)

    @property
    def retrain_recommended(self) -> bool:
        return self.alert


def classify(value: float) -> str:
    if value < STABLE_BELOW:
        return "stable"
    if value <= SIGNIFICANT_ABOVE:
        return "moderate"
    return "significant"


def check(
    numeric_reference: dict[str, npt.NDArray[np.float64]],
    numeric_current: dict[str, npt.NDArray[np.float64]],
    categorical_reference: dict[str, list[str]] | None = None,
    categorical_current: dict[str, list[str]] | None = None,
) -> DriftReport:
    findings: list[DriftFinding] = []
    for name, ref in numeric_reference.items():
        value = psi(ref, numeric_current[name])
        findings.append(DriftFinding(name, value, classify(value)))
    for name, ref_cats in (categorical_reference or {}).items():
        value = categorical_psi(ref_cats, (categorical_current or {})[name])
        findings.append(DriftFinding(name, value, classify(value)))
    return DriftReport(findings)
