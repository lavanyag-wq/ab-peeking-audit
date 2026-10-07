"""Simulate A/B experiments as cumulative daily counts, and the z statistics.

An experiment here is per_day subjects per arm per day, conversion
probabilities p_a and p_b, run for a number of days. The simulator returns
cumulative conversion counts per (trial, day), which is exactly the state a
dashboard shows at each peek. The z statistic is the pooled two-proportion
z, computed vectorized across all trials and days; a test pins it to
statsmodels' proportions_ztest value for value on a grid, so the fast engine
and the reference library cannot drift apart silently.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .errors import UsageError
from .rng import bernoulli_matrix

# Counter-space layout: one contiguous block per (day, arm), holding
# trials * per_day counters, so each block is generated with a single
# vectorized call and no block overlaps another. The layout means the random
# sample is a function of (seed, trials, design): the same seed with a
# different trial count is a different sample, which the experiments handle
# by fixing trials and which keeps every draw a pure function of its counter.


@dataclass(frozen=True)
class Design:
    days: int
    per_day: int  # subjects per arm per day
    p_a: float
    p_b: float

    def __post_init__(self):
        if self.days < 1:
            raise UsageError(f"days must be >= 1, got {self.days}")
        if self.per_day < 1:
            raise UsageError(f"per_day must be >= 1, got {self.per_day}")
        for name, p in (("p_a", self.p_a), ("p_b", self.p_b)):
            if not 0.0 < p < 1.0:
                raise UsageError(f"{name} must be in (0, 1), got {p}")

    @property
    def is_null(self) -> bool:
        return self.p_a == self.p_b


def cumulative_counts(design: Design, trials: int, seed: int) -> tuple[np.ndarray, np.ndarray]:
    """Cumulative conversions per (trial, day) for each arm."""
    if trials < 1:
        raise UsageError(f"trials must be >= 1, got {trials}")
    daily_a = np.empty((trials, design.days), dtype=np.int64)
    daily_b = np.empty((trials, design.days), dtype=np.int64)
    block = trials * design.per_day
    for day in range(design.days):
        for arm, out, p in ((0, daily_a, design.p_a), (1, daily_b, design.p_b)):
            start = (day * 2 + arm) * block
            draws = bernoulli_matrix(seed, start, trials, design.per_day, p)
            out[:, day] = draws.sum(axis=1)
    return daily_a.cumsum(axis=1), daily_b.cumsum(axis=1)


def pooled_z(conv_a: np.ndarray, conv_b: np.ndarray, nobs: np.ndarray) -> np.ndarray:
    """Pooled two-proportion z, elementwise; 0 where the pooled rate is degenerate.

    Matches statsmodels.stats.proportion.proportions_ztest with the pooled
    variance (its default); the equivalence is pinned by a test.
    """
    conv_a = np.asarray(conv_a, dtype=np.float64)
    conv_b = np.asarray(conv_b, dtype=np.float64)
    nobs = np.asarray(nobs, dtype=np.float64)
    pooled = (conv_a + conv_b) / (2.0 * nobs)
    var = pooled * (1.0 - pooled) * (2.0 / nobs)
    with np.errstate(divide="ignore", invalid="ignore"):
        z = (conv_a / nobs - conv_b / nobs) / np.sqrt(var)
    return np.where(var > 0.0, z, 0.0)


def z_matrix(design: Design, trials: int, seed: int) -> np.ndarray:
    """|z| per (trial, day): the dashboard's significance readout at every peek."""
    conv_a, conv_b = cumulative_counts(design, trials, seed)
    nobs = (np.arange(design.days) + 1) * design.per_day
    return np.abs(pooled_z(conv_a, conv_b, nobs[None, :]))
