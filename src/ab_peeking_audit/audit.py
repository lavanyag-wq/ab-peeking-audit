"""The audit: measure a decision procedure's false positive rate exactly once.

A procedure is a peek schedule plus a stopping rule: look at the dashboard on
the scheduled days, declare a winner the first time |z| crosses the critical
value, otherwise declare nothing at the horizon. The audit replays the
procedure over seeded null experiments and reports the fraction that declared
a winner, with an exact Clopper-Pearson interval, because a Monte Carlo rate
quoted without its resolution is a number wearing more precision than it has.

Three verdicts. CONSISTENT: the interval is compatible with the nominal
alpha. INFLATED: the interval's lower bound exceeds alpha, so the procedure
provably lies about its own error rate. INCONCLUSIVE: the interval contains
alpha but is too wide to exclude a doubled rate, so the trials cannot
distinguish an honest procedure from one twice as wrong, and the honest
output is "more trials", as its own machine-readable outcome.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy.stats import beta, norm

from .errors import UsageError
from .simulate import Design, z_matrix

POLICIES = ("single", "weekly", "daily")

VERDICT_CONSISTENT = "CONSISTENT"
VERDICT_INFLATED = "INFLATED"
VERDICT_INCONCLUSIVE = "INCONCLUSIVE"


def peek_days(policy: str, days: int) -> list[int]:
    """0-based day indices on which the procedure looks at the dashboard."""
    if days < 1:
        raise UsageError(f"days must be >= 1, got {days}")
    if policy == "single":
        return [days - 1]
    if policy == "weekly":
        return [d for d in range(6, days, 7)] + ([days - 1] if (days - 1) % 7 != 6 else [])
    if policy == "daily":
        return list(range(days))
    raise UsageError(f"unknown policy {policy!r}, expected one of {POLICIES}")


def critical_value(alpha: float) -> float:
    if not 0.0 < alpha < 1.0:
        raise UsageError(f"alpha must be in (0, 1), got {alpha}")
    return float(norm.ppf(1.0 - alpha / 2.0))


def declared(z: np.ndarray, peeks: list[int], crit: float) -> np.ndarray:
    """Per trial: did the procedure declare a winner at any scheduled peek?"""
    if max(peeks) >= z.shape[1] or min(peeks) < 0:
        raise UsageError(f"peek days {peeks} out of range for {z.shape[1]} days")
    return (z[:, peeks] >= crit).any(axis=1)


def clopper_pearson(successes: int, trials: int, confidence: float = 0.95) -> tuple[float, float]:
    """Exact binomial interval; the standard inversion of two beta tails."""
    if trials < 1 or not 0 <= successes <= trials:
        raise UsageError(f"invalid counts: {successes}/{trials}")
    lo = 0.0 if successes == 0 else float(beta.ppf((1 - confidence) / 2, successes,
                                                   trials - successes + 1))
    hi = 1.0 if successes == trials else float(beta.ppf(1 - (1 - confidence) / 2,
                                                        successes + 1, trials - successes))
    return lo, hi


@dataclass(frozen=True)
class FprResult:
    policy: str
    n_peeks: int
    alpha: float
    trials: int
    false_positives: int
    fpr: float
    ci_low: float
    ci_high: float
    verdict: str


def audit_policy(design: Design, policy: str, alpha: float, trials: int,
                 seed: int) -> FprResult:
    """Measure the procedure's false positive rate. Requires a null design."""
    if not design.is_null:
        raise UsageError("auditing a false positive rate requires p_a == p_b; "
                         f"got {design.p_a} and {design.p_b}")
    peeks = peek_days(policy, design.days)
    z = z_matrix(design, trials, seed)
    wins = declared(z, peeks, critical_value(alpha))
    false_positives = int(wins.sum())
    fpr = false_positives / trials
    lo, hi = clopper_pearson(false_positives, trials)
    if lo > alpha:
        verdict = VERDICT_INFLATED
    elif hi <= 2.0 * alpha:
        verdict = VERDICT_CONSISTENT
    else:
        verdict = VERDICT_INCONCLUSIVE
    return FprResult(policy, len(peeks), alpha, trials, false_positives,
                     fpr, lo, hi, verdict)
