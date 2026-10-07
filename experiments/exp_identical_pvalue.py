"""Experiment: the final report reads the same either way; that is the point.

Question the README asks: what does a final p-value fail to carry? Under the
null with daily peeking, collect every trial the naive rule stopped early and
record the p-value at the stopping peek, the stopping day, and what the
p-value would read if the experiment had been left to run to its horizon.
Compare against the p-values of single-look false positives. The two
populations of reported numbers overlap completely: nothing in "p = 0.03,
n per arm = N" says which procedure produced it. The evaporation share is
the sharpest single number: among early-stopped null wins, how many are no
longer significant at the planned horizon. Writes
docs/experiments/identical_pvalue.json.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
from scipy.stats import norm

from ab_peeking_audit.audit import critical_value, peek_days
from ab_peeking_audit.boundary import stop_profile
from ab_peeking_audit.simulate import Design, z_matrix

OUT = Path(__file__).resolve().parent.parent / "docs" / "experiments" / "identical_pvalue.json"
NULL = Design(days=28, per_day=400, p_a=0.05, p_b=0.05)
TRIALS = 4000
SEED = 7


def two_sided_p(z: np.ndarray) -> np.ndarray:
    return 2.0 * (1.0 - norm.cdf(z))


def main() -> None:
    z = z_matrix(NULL, TRIALS, SEED)
    crit = critical_value(0.05)
    daily = peek_days("daily", NULL.days)

    sig = z >= crit
    early_win = sig.any(axis=1)
    stop_days = stop_profile(z, daily, crit)          # 0-based
    stop_z = z[early_win, :][np.arange(early_win.sum()), stop_days]
    stop_p = two_sided_p(stop_z)
    final_p_of_winners = two_sided_p(z[early_win, -1])
    evaporated = final_p_of_winners > 0.05

    single_win = z[:, -1] >= crit
    single_win_p = two_sided_p(z[single_win, -1])

    payload = {
        "alpha": 0.05, "trials": TRIALS, "seed": SEED,
        "daily_early_wins": int(early_win.sum()),
        "median_stop_day": int(np.median(stop_days)) + 1,
        "median_stop_p": round(float(np.median(stop_p)), 4),
        "stop_p_quartiles": [round(float(q), 4) for q in
                             np.percentile(stop_p, [25, 50, 75])],
        "single_look_wins": int(single_win.sum()),
        "median_single_win_p": round(float(np.median(single_win_p)), 4),
        "single_win_p_quartiles": [round(float(q), 4) for q in
                                   np.percentile(single_win_p, [25, 50, 75])],
        "evaporated": int(evaporated.sum()),
        "evaporated_pct": round(100 * float(evaporated.mean()), 1),
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, indent=1, sort_keys=True))
    print(f"daily-peek null wins: {payload['daily_early_wins']} of {TRIALS}; "
          f"median stop day {payload['median_stop_day']}, "
          f"median reported p {payload['median_stop_p']}")
    print(f"single-look null wins: {payload['single_look_wins']}; "
          f"median reported p {payload['median_single_win_p']}")
    print(f"reported-p quartiles, peeked {payload['stop_p_quartiles']} vs "
          f"single {payload['single_win_p_quartiles']}: same numbers, "
          f"different error rates")
    print(f"evaporated by the horizon: {payload['evaporated']} of "
          f"{payload['daily_early_wins']} ({payload['evaporated_pct']}%)")
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
