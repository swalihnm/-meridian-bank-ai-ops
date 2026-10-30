"""Experiment statistics: deterministic assignment, intervals, tests and sample size.

Method notes are in docs/product/STATS_NOTES.md. Everything here is plain math so it can be checked
by hand; the tests use hand-computed values.
"""

from __future__ import annotations

import hashlib
import math

from scipy.stats import binom, norm


def assign_variant(unit_id: str, experiment: str, variants: tuple[str, ...] = ("A", "B")) -> str:
    """Stable assignment: the same unit always gets the same variant for the same experiment."""
    digest = hashlib.sha256(f"{experiment}:{unit_id}".encode()).digest()
    return variants[int.from_bytes(digest[:8], "big") % len(variants)]


def wilson_interval(successes: int, n: int, z: float = 1.959964) -> tuple[float, float]:
    """95 percent Wilson score interval for a proportion."""
    if n == 0:
        raise ValueError("n must be positive")
    p = successes / n
    denom = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / denom
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return max(0.0, centre - half), min(1.0, centre + half)


def two_proportion_z(x1: int, n1: int, x2: int, n2: int) -> tuple[float, float]:
    """Two-sided z-test for the difference p2 - p1. Returns (difference, p_value)."""
    p1, p2 = x1 / n1, x2 / n2
    pooled = (x1 + x2) / (n1 + n2)
    se = math.sqrt(pooled * (1 - pooled) * (1 / n1 + 1 / n2))
    if se == 0:
        return p2 - p1, 1.0
    z = (p2 - p1) / se
    return p2 - p1, 2 * (1 - norm.cdf(abs(z)))


def mcnemar_exact(b: int, c: int) -> float:
    """Exact two-sided McNemar test on discordant pairs. b and c are the two discordant counts."""
    n = b + c
    if n == 0:
        return 1.0
    k = min(b, c)
    return min(1.0, 2 * float(binom.cdf(k, n, 0.5)))


def sample_size_per_arm(
    p_base: float, min_effect: float, alpha: float = 0.05, power: float = 0.8
) -> int:
    """Per-arm sample size to detect an absolute change `min_effect` from `p_base` (two-sided)."""
    p_alt = p_base + min_effect
    z_a = norm.ppf(1 - alpha / 2)
    z_b = norm.ppf(power)
    var = p_base * (1 - p_base) + p_alt * (1 - p_alt)
    return math.ceil(((z_a + z_b) ** 2) * var / (min_effect**2))
