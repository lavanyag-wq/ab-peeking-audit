# ADR-003: statsmodels is the reference implementation, not the engine

Status: accepted

## Decision

The Monte Carlo engine computes the pooled two-proportion z itself,
vectorized over all trials and days. statsmodels supplies the reference:
`proportions_ztest` in the single-experiment replay path, the power
machinery for fixed-horizon sample size, and a test pins the engine's z
equal to the library's on a grid of counts.

## The alternative

Call statsmodels inside the Monte Carlo loop, which would make the library
the engine.

## Why

Scale and meaning, in that order. The audit evaluates the test at every
(trial, day) cell: 4000 trials by 28 days per policy, repeated for
calibration, holdout and power, so per-cell Python calls would turn a
two-second measurement into minutes and push trial counts down, widening
every published interval. But speed alone would not justify a reimplementation:
the justification is the equivalence test. With the pin in place, the fast
engine provably measures the same statistic teams compute with the standard
library, so the Monte Carlo results are statements about the test people
actually run, not about a lookalike. If either side ever changes definition,
the pin fails loudly.

The division of labour also keeps the library where it adds unique value:
`proportions_ztest` is what a reader will reproduce by hand on one peek of
the replay, and `NormalIndPower` supplies the sample-size context that
anchors the power table to practice.
