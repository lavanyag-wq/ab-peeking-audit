# ADR-002: A simulation-calibrated constant boundary, scored on held-out nulls

Status: accepted

## Decision

The corrected procedure raises the per-peek critical value to a constant z*
found by bisection against simulated null experiments, then reports the
achieved false positive rate on a second sample with a different seed. The
calibration seed and the holdout seed are required to differ; equal seeds
are refused.

## The alternative

Closed-form group-sequential boundaries: Pocock (also a constant) or
O'Brien-Fleming (spends alpha late, preserving more power at the horizon),
with alpha-spending functions for irregular schedules.

## Why simulation here

Three reasons. The closed forms assume equal information increments and
normal increments; this schedule satisfies both only approximately (binomial
counts, a first peek at one day of data), and the simulation prices the
approximation instead of inheriting it. Second, the calibration is checked
by construction: the holdout measurement is the same audit the tool applies
to naive procedures, so the corrected boundary is held to exactly the
standard it enforces. Third, defensibility: a bisection against the measured
rate is explainable in one sentence; an alpha-spending derivation is not,
and this repository's referee for every claim is a measurement.

What the closed form would buy is real and stated: O'Brien-Fleming would
keep more of the single-look power than a constant boundary does, so the
17.5 point power cost published here is the price of the simple correction,
not the cheapest possible honest procedure. That refinement is future work
with a measurement already set up to score it.

## Why the holdout is not optional

A threshold tuned and scored on the same draws inherits their noise in its
favour: the bisection lands exactly where the calibration sample's rate
touches alpha, so in-sample achieved rate is alpha by construction and says
nothing. The held-out rate (4.05% here) is the number with content.
