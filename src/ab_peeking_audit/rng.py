"""A counter-based PRNG owned by the repository, so receipts outlive libraries.

Every figure this package publishes is a Monte Carlo measurement, and the
receipts pipeline re-measures them on every CI run. NumPy's Generator does
not promise identical streams across library versions, which would let a
numpy upgrade silently change every published number. SplitMix64 is twenty
lines, counter-based (stateless, so draw i is a pure function of (seed, i)
and any slice can be generated in parallel or out of order), and its output
is fixed by arithmetic this file owns. Statistical quality is an assumption,
stated in ADR-001: SplitMix64 passes standard test batteries and is the
seeding primitive of mainstream generators, which is sufficient quality for
estimating binomial tail rates at the fourth decimal place.
"""

from __future__ import annotations

import numpy as np

from .errors import UsageError

_GAMMA = np.uint64(0x9E3779B97F4A7C15)
_M1 = np.uint64(0xBF58476D1CE4E5B9)
_M2 = np.uint64(0x94D049BB133111EB)
_SHIFT_SCALE = np.float64(2.0**-53)


def _mix(x: np.ndarray) -> np.ndarray:
    z = (x + _GAMMA) * np.uint64(1)
    z = (z ^ (z >> np.uint64(30))) * _M1
    z = (z ^ (z >> np.uint64(27))) * _M2
    return z ^ (z >> np.uint64(31))


def uniforms(seed: int, start: int, count: int) -> np.ndarray:
    """count uniforms in [0, 1), draws [start, start + count) of stream `seed`."""
    if count < 0 or start < 0:
        raise UsageError(f"start and count must be >= 0, got {start}, {count}")
    if seed < 0:
        raise UsageError(f"seed must be >= 0, got {seed}")
    counters = np.arange(start, start + count, dtype=np.uint64)
    seeded = counters ^ _mix(np.uint64(seed) * np.ones(1, dtype=np.uint64))
    return (_mix(seeded) >> np.uint64(11)).astype(np.float64) * _SHIFT_SCALE


def bernoulli_matrix(seed: int, start: int, rows: int, cols: int, p: float) -> np.ndarray:
    """rows x cols of {0,1} draws with P[1] = p, consuming rows*cols counters."""
    if not 0.0 <= p <= 1.0:
        raise UsageError(f"p must be in [0, 1], got {p}")
    return (uniforms(seed, start, rows * cols) < p).reshape(rows, cols).astype(np.int64)
