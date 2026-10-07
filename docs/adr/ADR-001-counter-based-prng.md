# ADR-001: A twenty-line counter-based PRNG instead of a library generator

Status: accepted

## Decision

All randomness comes from SplitMix64 implemented in `rng.py` as a pure
function of (seed, counter), vectorized over numpy uint64 arithmetic. No
numpy Generator, no global state.

## The alternative

numpy's PCG64 Generator, which is better studied and faster to reach for.

## Why

Every published figure in this repository is a Monte Carlo measurement, and
the receipts pipeline re-measures all of them on every CI run and fails the
build if a document disagrees. numpy's stability policy does not promise
identical streams for distribution methods across library versions, so a
routine numpy upgrade could legally change every published number at once,
turning the receipts check into a periodic false alarm. Owning the twenty
lines removes the dependency of the numbers on anyone's release notes, and
counter-based form adds two properties worth having anyway: draw i is a pure
function of (seed, i), so any slice can be generated independently (a test
pins this), and parallel or out-of-order generation cannot change results.

A single known draw is pinned in the test suite, so a silent change to the
generator turns every downstream figure into a red build rather than a quiet
drift.

## The assumption, stated

SplitMix64's statistical quality is taken from the literature, not re-proven
here: it passes standard test batteries and serves as the seeding primitive
of mainstream generators. The quantities estimated are binomial tail rates
over at most a few hundred million draws, far inside that quality margin.
The suite still asserts the gross properties (uniform mean, bernoulli rate,
single-look false positive rate near alpha) so a transcription error in the
constants would not survive.
