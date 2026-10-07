"""Command line interface. The exit code names the audit outcome.

audit measures a procedure's false positive rate and exits 0 (CONSISTENT with
the nominal alpha), 1 (INFLATED: the exact interval excludes alpha from
below, the procedure lies), 2 (INCONCLUSIVE: the interval contains alpha but
cannot rule out a doubled rate; run more trials), or 3 (error). boundary
calibrates the constant z* that makes the schedule honest and reports the
held-out achieved rate. replay prints one experiment's decision log: the
record a final p-value cannot carry.
"""

from __future__ import annotations

import argparse
import sys

from .analysis import fixed_horizon_n, replay
from .audit import (
    VERDICT_CONSISTENT,
    VERDICT_INFLATED,
    audit_policy,
)
from .boundary import calibrate_boundary
from .errors import (
    EXIT_CONSISTENT,
    EXIT_ERROR,
    EXIT_INCONCLUSIVE,
    EXIT_INFLATED,
    AuditError,
)
from .simulate import Design


def _design(args: argparse.Namespace, p_b: float | None = None) -> Design:
    return Design(days=args.days, per_day=args.per_day, p_a=args.base_rate,
                  p_b=args.base_rate if p_b is None else p_b)


def _cmd_audit(args: argparse.Namespace) -> int:
    result = audit_policy(_design(args), args.policy, args.alpha, args.trials, args.seed)
    print(f"policy: {args.policy} ({result.n_peeks} peeks over {args.days} days)")
    print(f"measured false positive rate: {result.fpr:.4f} "
          f"[{result.ci_low:.4f}, {result.ci_high:.4f}] exact 95% interval, "
          f"{result.trials} null trials")
    print(f"nominal alpha: {result.alpha}")
    print(f"verdict: {result.verdict}")
    if result.verdict == VERDICT_CONSISTENT:
        return EXIT_CONSISTENT
    if result.verdict == VERDICT_INFLATED:
        return EXIT_INFLATED
    return EXIT_INCONCLUSIVE


def _cmd_boundary(args: argparse.Namespace) -> int:
    cal = calibrate_boundary(_design(args), args.policy, args.alpha, args.trials,
                             args.seed, args.holdout_seed)
    print(f"policy: {args.policy}, nominal alpha {cal.alpha}")
    print(f"calibrated z*: {cal.z_star:.3f} (per-peek alpha {cal.per_peek_alpha:.5f})")
    print(f"held-out false positive rate: {cal.holdout_fpr:.4f} "
          f"[{cal.holdout_ci_low:.4f}, {cal.holdout_ci_high:.4f}]")
    return EXIT_CONSISTENT


def _cmd_replay(args: argparse.Namespace) -> int:
    lifted = None if args.lift == 0.0 else args.base_rate + args.lift
    r = replay(_design(args, lifted), args.policy, args.seed, trial=0,
               alpha=args.alpha, z_star=args.z_star)
    print(f"{'day':>4} {'n/arm':>7} {'conv A':>7} {'conv B':>7} {'p':>8}  naive  corrected")
    for rec in r.records:
        print(f"{rec.day:>4} {rec.nobs_per_arm:>7} {rec.conv_a:>7} {rec.conv_b:>7} "
              f"{rec.p_value:>8.4f}  {'STOP' if rec.naive_significant else '.':>5}  "
              f"{'STOP' if rec.corrected_significant else '.':>9}")
    naive = r.naive_stop_day
    corrected = r.corrected_stop_day
    print(f"naive rule: {'declares on day ' + str(naive) if naive else 'never declares'}; "
          f"corrected boundary: "
          f"{'declares on day ' + str(corrected) if corrected else 'never declares'}")
    print(f"final-day p: {r.final_p:.4f} (this number is all a report keeps)")
    return EXIT_CONSISTENT


def _cmd_samplesize(args: argparse.Namespace) -> int:
    n = fixed_horizon_n(args.base_rate, args.base_rate + args.lift,
                        alpha=args.alpha, power_target=args.power)
    print(f"fixed-horizon per-arm n for {args.power:.0%} power at "
          f"{args.base_rate} vs {args.base_rate + args.lift}: {n}")
    return EXIT_CONSISTENT


def _common(p: argparse.ArgumentParser) -> None:
    p.add_argument("--days", type=int, default=28)
    p.add_argument("--per-day", type=int, default=400)
    p.add_argument("--base-rate", type=float, default=0.05)
    p.add_argument("--alpha", type=float, default=0.05)
    p.add_argument("--seed", type=int, default=7)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="peek-audit",
                                     description="A/B decision procedure auditor")
    sub = parser.add_subparsers(dest="command", required=True)

    p_audit = sub.add_parser("audit", help="measure a procedure's false positive rate")
    _common(p_audit)
    p_audit.add_argument("--policy", default="daily")
    p_audit.add_argument("--trials", type=int, default=4000)
    p_audit.set_defaults(func=_cmd_audit)

    p_b = sub.add_parser("boundary", help="calibrate the honest z* for a schedule")
    _common(p_b)
    p_b.add_argument("--policy", default="daily")
    p_b.add_argument("--trials", type=int, default=4000)
    p_b.add_argument("--holdout-seed", type=int, default=8)
    p_b.set_defaults(func=_cmd_boundary)

    p_r = sub.add_parser("replay", help="one experiment's decision log, per peek")
    _common(p_r)
    p_r.add_argument("--policy", default="daily")
    p_r.add_argument("--lift", type=float, default=0.0)
    p_r.add_argument("--z-star", type=float, default=2.731)
    p_r.set_defaults(func=_cmd_replay)

    p_n = sub.add_parser("samplesize", help="fixed-horizon n via statsmodels")
    _common(p_n)
    p_n.add_argument("--lift", type=float, required=True)
    p_n.add_argument("--power", type=float, default=0.8)
    p_n.set_defaults(func=_cmd_samplesize)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return args.func(args)
    except AuditError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return EXIT_ERROR


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
