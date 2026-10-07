# ADR-004: INCONCLUSIVE is a verdict with its own exit code, not a pass

Status: accepted

## Decision

The audit exits 0 (CONSISTENT), 1 (INFLATED), 2 (INCONCLUSIVE), 3 (error).
INFLATED requires the exact interval's lower bound to exceed alpha.
CONSISTENT requires the interval to lie at or below twice alpha.
INCONCLUSIVE is the remainder: the interval contains alpha but cannot
exclude a doubled rate.

## The alternative

A point-estimate comparison (measured rate above alpha means inflated), or
a two-way pass/fail.

## Why intervals and a third verdict

A Monte Carlo rate is an estimate wearing its sample size, and a point
comparison converts estimation noise into verdicts: at 60 trials, a measured
6.7% would read as "inflated" and a measured 3.3% as "fine", when the data
cannot distinguish either from 5%. Requiring the interval to clear alpha
before saying INFLATED makes the accusation provable; requiring it to stay
under twice alpha before saying CONSISTENT keeps the tool from certifying a
procedure its own trial budget cannot actually vouch for. The remainder is
INCONCLUSIVE with exit 2, so a pipeline can distinguish "needs more trials"
from both findings without parsing text.

Twice alpha is a policy choice, visible and arguable: it says the audit will
not call a procedure honest while a 2x error rate is still on the table. A
stricter multiplier buys stronger certification for more trials; the
constant sits in one place in `audit.py`.

Exit 3 stays separate so that a crash is never confused with a finding, in
either direction.
