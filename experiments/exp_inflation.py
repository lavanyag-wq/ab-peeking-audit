"""Experiment: the false positive rate of each peeking cadence, measured.

Question the README asks: at a nominal alpha of 0.05, what error rate does
each decision procedure actually run? One null design (28 days, 400 subjects
per arm per day, base rate 0.05), 4000 seeded null experiments per policy,
exact Clopper-Pearson intervals. Writes docs/experiments/inflation.json.
"""

from __future__ import annotations

import json
from pathlib import Path

from ab_peeking_audit.audit import audit_policy
from ab_peeking_audit.simulate import Design

OUT = Path(__file__).resolve().parent.parent / "docs" / "experiments" / "inflation.json"
NULL = Design(days=28, per_day=400, p_a=0.05, p_b=0.05)
TRIALS = 4000
SEED = 7


def main() -> None:
    rows = []
    for policy in ("single", "weekly", "daily"):
        r = audit_policy(NULL, policy, 0.05, TRIALS, SEED)
        rows.append({
            "policy": policy,
            "peeks": r.n_peeks,
            "false_positives": r.false_positives,
            "fpr_pct": round(100 * r.fpr, 2),
            "ci_low_pct": round(100 * r.ci_low, 2),
            "ci_high_pct": round(100 * r.ci_high, 2),
            "verdict": r.verdict,
        })
    payload = {"alpha": 0.05, "trials": TRIALS, "seed": SEED,
               "design": {"days": NULL.days, "per_day": NULL.per_day,
                          "base_rate": NULL.p_a}, "rows": rows}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, indent=1, sort_keys=True))
    print(f"{'policy':<8} {'peeks':>6} {'measured FPR':>13} {'exact 95% CI':>18}  verdict")
    for r in rows:
        print(f"{r['policy']:<8} {r['peeks']:>6} {r['fpr_pct']:>12.2f}% "
              f"[{r['ci_low_pct']:>5.2f}%, {r['ci_high_pct']:>5.2f}%]  {r['verdict']}")
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
