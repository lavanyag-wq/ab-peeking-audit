"""ab-peeking-audit: measuring the number a final p-value cannot contain.

A reported p-value is a function of the final counts. The decision procedure
that produced it (how many times the experiment was peeked at, and whether a
significant peek stopped it) is not in the counts, so the report structurally
cannot reveal its own false positive rate: p = 0.03 at n = 22,400 reads
identically whether it came from one pre-registered look or from the 17th
daily peek that finally crossed the line. This package replays decision
procedures under the null and measures what the report cannot carry: the
procedure's actual false positive rate, with an exact confidence interval,
plus a simulation-calibrated boundary that restores the nominal alpha and a
measurement of what that correction costs in power.
"""

__version__ = "0.1.0"
