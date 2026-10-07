"""Experiment: the boundary that restores alpha, and the power it costs.

Question the README asks: what does honest peeking cost? Calibrate the
constant boundary for the daily schedule on one seed, measure its held-out
false positive rate on another, then measure power at a real effect (base
rate 0.05 against 0.0575) for three procedures on the same experiments: one
pre-registered look, naive daily peeking (invalid, shown for scale), and
corrected daily peeking. statsmodels' power machinery supplies the
fixed-horizon sample size for context. Writes
docs/experiments/correction_cost.json.
"""

from __future__ import annotations

import json
from pathlib import Path

from ab_peeking_audit.analysis import fixed_horizon_n
from ab_peeking_audit.audit import critical_value
from ab_peeking_audit.boundary import calibrate_boundary, power
from ab_peeking_audit.simulate import Design

OUT = Path(__file__).resolve().parent.parent / "docs" / "experiments" / "correction_cost.json"
NULL = Design(days=28, per_day=400, p_a=0.05, p_b=0.05)
LIFT = Design(days=28, per_day=400, p_a=0.05, p_b=0.0575)
TRIALS = 4000


def main() -> None:
    cal = calibrate_boundary(NULL, "daily", 0.05, TRIALS, seed=11, holdout_seed=12)
    crit = critical_value(0.05)
    rows = []
    for name, policy, threshold, valid in (
        ("single pre-registered look", "single", crit, True),
        ("naive daily peeking", "daily", crit, False),
        ("corrected daily peeking", "daily", cal.z_star, True),
    ):
        p, lo, hi = power(LIFT, policy, threshold, TRIALS, seed=21)
        rows.append({"procedure": name, "threshold": round(threshold, 3),
                     "valid": valid, "power_pct": round(100 * p, 1),
                     "ci_low_pct": round(100 * lo, 1),
                     "ci_high_pct": round(100 * hi, 1)})
    horizon_n = LIFT.days * LIFT.per_day
    payload = {
        "alpha": 0.05, "trials": TRIALS,
        "effect": {"p_a": LIFT.p_a, "p_b": LIFT.p_b},
        "z_star": round(cal.z_star, 3),
        "per_peek_alpha": round(cal.per_peek_alpha, 5),
        "holdout_fpr_pct": round(100 * cal.holdout_fpr, 2),
        "holdout_ci": [round(100 * cal.holdout_ci_low, 2),
                       round(100 * cal.holdout_ci_high, 2)],
        "horizon_n_per_arm": horizon_n,
        "fixed_horizon_n_80pct": fixed_horizon_n(LIFT.p_a, LIFT.p_b),
        "rows": rows,
        "power_cost_points": round(rows[0]["power_pct"] - rows[2]["power_pct"], 1),
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, indent=1, sort_keys=True))
    print(f"calibrated z* {payload['z_star']} (per-peek alpha "
          f"{payload['per_peek_alpha']}), held-out FPR {payload['holdout_fpr_pct']}% "
          f"[{payload['holdout_ci'][0]}%, {payload['holdout_ci'][1]}%]")
    print(f"{'procedure':<28} {'threshold':>10} {'valid':>6} {'power':>8}")
    for r in rows:
        print(f"{r['procedure']:<28} {r['threshold']:>10.3f} "
              f"{'yes' if r['valid'] else 'NO':>6} {r['power_pct']:>7.1f}%")
    print(f"power cost of honest daily peeking vs one look: "
          f"{payload['power_cost_points']} points "
          f"(horizon n/arm {horizon_n}; statsmodels fixed-horizon n for 80%: "
          f"{payload['fixed_horizon_n_80pct']})")
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
