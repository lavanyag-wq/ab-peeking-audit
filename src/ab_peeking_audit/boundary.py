"""Calibrate the boundary that makes peeking honest, and price what it costs.

The corrected procedure keeps the peek schedule and raises the critical value
to a constant z* chosen so that the whole procedure's false positive rate is
the nominal alpha. z* is found by bisection against a calibration sample of
null experiments, then measured on a held-out sample with a different seed,
because a threshold tuned and scored on the same draws inherits their noise
in its favour. A closed-form group-sequential boundary (O'Brien-Fleming)
exists; ADR-002 explains why a simulation-calibrated constant is the choice
here and what the closed form would buy.

Power is measured the same way: fraction of seeded non-null experiments the
procedure declares, so the correction's price is a measured number, not a
footnote.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .audit import clopper_pearson, declared, peek_days
from .errors import UsageError
from .simulate import Design, z_matrix


@dataclass(frozen=True)
class Calibration:
    policy: str
    alpha: float
    z_star: float
    per_peek_alpha: float
    calibration_trials: int
    holdout_fpr: float
    holdout_ci_low: float
    holdout_ci_high: float


def calibrate_boundary(design: Design, policy: str, alpha: float, trials: int,
                       seed: int, holdout_seed: int) -> Calibration:
    """Bisect z* on one sample, measure the achieved rate on another."""
    if not design.is_null:
        raise UsageError("calibration requires a null design")
    if holdout_seed == seed:
        raise UsageError("holdout_seed must differ from seed; measuring on the "
                         "calibration sample flatters the boundary")
    peeks = peek_days(policy, design.days)
    z_cal = z_matrix(design, trials, seed)

    def fpr_at(threshold: float) -> float:
        return float(declared(z_cal, peeks, threshold).mean())

    lo, hi = 1.0, 6.0
    for _ in range(40):
        mid = (lo + hi) / 2.0
        if fpr_at(mid) > alpha:
            lo = mid
        else:
            hi = mid
    z_star = hi  # the smallest tested threshold whose calibration FPR <= alpha

    z_hold = z_matrix(design, trials, holdout_seed)
    wins = int(declared(z_hold, peeks, z_star).sum())
    ci_low, ci_high = clopper_pearson(wins, trials)
    from scipy.stats import norm
    per_peek_alpha = float(2.0 * (1.0 - norm.cdf(z_star)))
    return Calibration(policy, alpha, float(z_star), per_peek_alpha, trials,
                       wins / trials, ci_low, ci_high)


def power(design: Design, policy: str, threshold: float, trials: int,
          seed: int) -> tuple[float, float, float]:
    """Fraction of non-null experiments declared, with its exact interval."""
    if design.is_null:
        raise UsageError("power requires p_a != p_b")
    peeks = peek_days(policy, design.days)
    z = z_matrix(design, trials, seed)
    wins = int(declared(z, peeks, threshold).sum())
    lo, hi = clopper_pearson(wins, trials)
    return wins / trials, lo, hi


def stop_profile(z: np.ndarray, peeks: list[int], threshold: float) -> np.ndarray:
    """Per declaring trial, the 0-based day it stopped on (first crossing)."""
    sig = z[:, peeks] >= threshold
    any_win = sig.any(axis=1)
    first = sig.argmax(axis=1)
    return np.array(peeks, dtype=np.int64)[first[any_win]]
