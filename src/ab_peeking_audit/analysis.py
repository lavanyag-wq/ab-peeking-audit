"""Single-experiment analysis through statsmodels, and the replay that shows
what the final report forgot.

The Monte Carlo engine computes its own vectorized pooled z for speed; this
module is the reference path: statsmodels' proportions_ztest for each peek of
one experiment, and statsmodels' power machinery for the fixed-horizon sample
size context. A test pins the engine's z to the library's z on a grid, so
the fast path and the reference cannot drift apart. The replay produces the
decision log a final report throws away: every peek's p-value, the day the
naive rule would have stopped, and what the corrected boundary concludes on
the same data.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from statsmodels.stats.power import NormalIndPower
from statsmodels.stats.proportion import proportion_effectsize, proportions_ztest

from .audit import peek_days
from .errors import UsageError
from .simulate import Design, cumulative_counts


def reference_p_value(conv_a: int, conv_b: int, nobs: int) -> float:
    """Two-sided pooled two-proportion p, straight from statsmodels."""
    if nobs < 1:
        raise UsageError(f"nobs must be >= 1, got {nobs}")
    if conv_a == conv_b == 0 or conv_a == conv_b == nobs:
        return 1.0  # degenerate pooled rate; the engine's z is defined as 0 here
    _stat, p = proportions_ztest([conv_a, conv_b], [nobs, nobs])
    return float(p)


def fixed_horizon_n(p_a: float, p_b: float, alpha: float = 0.05,
                    power_target: float = 0.8) -> int:
    """Per-arm sample size for a single pre-registered look, via statsmodels."""
    if p_a == p_b:
        raise UsageError("sample size for a zero effect is undefined")
    effect = proportion_effectsize(p_a, p_b)
    n = NormalIndPower().solve_power(effect_size=effect, alpha=alpha,
                                     power=power_target, ratio=1.0)
    return int(np.ceil(float(n)))


@dataclass(frozen=True)
class PeekRecord:
    day: int  # 1-based for humans
    nobs_per_arm: int
    conv_a: int
    conv_b: int
    p_value: float
    naive_significant: bool
    corrected_significant: bool


@dataclass(frozen=True)
class Replay:
    design_days: int
    alpha: float
    z_star: float
    records: tuple[PeekRecord, ...]

    @property
    def naive_stop_day(self) -> int | None:
        for r in self.records:
            if r.naive_significant:
                return r.day
        return None

    @property
    def corrected_stop_day(self) -> int | None:
        for r in self.records:
            if r.corrected_significant:
                return r.day
        return None

    @property
    def final_p(self) -> float:
        return self.records[-1].p_value


def replay(design: Design, policy: str, seed: int, trial: int, alpha: float,
           z_star: float, trials: int = 1) -> Replay:
    """Replay one experiment's decision sequence with per-peek statsmodels p."""
    if trial < 0 or trial >= trials:
        raise UsageError(f"trial {trial} out of range for {trials} trials")
    conv_a, conv_b = cumulative_counts(design, trials, seed)
    from scipy.stats import norm
    records = []
    for day in peek_days(policy, design.days):
        nobs = (day + 1) * design.per_day
        a, b = int(conv_a[trial, day]), int(conv_b[trial, day])
        p = reference_p_value(a, b, nobs)
        z_abs = abs(float(norm.ppf(p / 2.0))) if p < 1.0 else 0.0
        records.append(PeekRecord(day + 1, nobs, a, b, p,
                                  p <= alpha, z_abs >= z_star))
    return Replay(design.days, alpha, z_star, tuple(records))
