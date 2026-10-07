"""Collect every figure the documents quote, from machine-readable outputs.

Nothing here is typed by hand: test count and coverage come from the junit
XML and coverage JSON pytest wrote (or writes here unless --skip-tests says
CI ran them as their own step); every other figure is read from the JSON the
experiments wrote. Derived values are computed in this one file.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REPORTS = ROOT / "reports"
EXPERIMENTS = ROOT / "docs" / "experiments"
OUT = ROOT / "docs" / "metrics.json"

ANCHORS = {
    "tests_total": ["{} tests", "{} property-named tests"],
    "coverage_line_pct": ["{}% line coverage", "coverage of {}%"],
    "trials": ["{} seeded null experiments", "{} null experiments", "{} experiments per"],
    "fpr_single_pct": ["look runs {}%", "single look at {}%"],
    "fpr_weekly_pct": ["weekly peeking runs {}%", "weekly at {}%"],
    "fpr_daily_pct": ["daily peeking runs {}%", "runs a {}% false positive"],
    "daily_ci_low_pct": ["floor at {}%"],
    "daily_ci_high_pct": ["ceiling at {}%"],
    "holdout_ci_low_pct": ["holdout floor at {}%"],
    "holdout_ci_high_pct": ["holdout ceiling at {}%"],
    "early_wins": ["{} early wins", "stopped early in {}", "{} of the daily-peeked"],
    "median_stop_day": ["median stop day of {}", "stops at day {}"],
    "evaporated_pct": ["{}% of them are no longer", "{}% of those wins evaporate",
                       "{}% evaporate"],
    "median_stop_p": ["median reported p of {}", "peeked median {}"],
    "median_single_p": ["single-look median of {}", "median win p of {}"],
    "z_star": ["constant z* of {}", "z* = {}", "boundary of {}"],
    "per_peek_alpha": ["per-peek alpha of {}"],
    "holdout_fpr_pct": ["held-out rate of {}%", "{}% on held-out nulls"],
    "power_single_pct": ["look wins {}%", "single look's {}%"],
    "power_naive_pct": ["claims {}%", "advertises {}%"],
    "power_corrected_pct": ["peeking wins {}%", "falls to {}%"],
    "power_cost_points": ["costs {} points", "{} points of power"],
    "horizon_n_per_arm": ["{} subjects per arm at the horizon", "n per arm of {}"],
    "fixed_horizon_n_80pct": ["needs {} per arm", "{} per arm for 80%"],
}


def _fmt(value) -> str:
    if isinstance(value, float):
        return f"{value:g}"
    return str(value)


def run_tests() -> None:
    REPORTS.mkdir(exist_ok=True)
    subprocess.run(
        [sys.executable, "-m", "pytest", "--junitxml", str(REPORTS / "junit.xml"),
         "--cov=ab_peeking_audit", f"--cov-report=json:{REPORTS / 'coverage.json'}",
         "-q"], check=True, cwd=ROOT)


def run_experiments() -> None:
    for script in sorted((ROOT / "experiments").glob("exp_*.py")):
        subprocess.run([sys.executable, str(script)], check=True, cwd=ROOT)


def collect(skip_tests: bool, skip_experiments: bool) -> dict:
    if not skip_tests:
        run_tests()
    if not skip_experiments:
        run_experiments()
    junit = ET.parse(REPORTS / "junit.xml").getroot()
    suite = junit if junit.tag == "testsuite" else junit.find("testsuite")
    failures = int(suite.get("failures", 0)) + int(suite.get("errors", 0))
    if failures:
        raise SystemExit(f"refusing to collect metrics from a failing suite ({failures} failed)")
    coverage = json.loads((REPORTS / "coverage.json").read_text())

    inflation = json.loads((EXPERIMENTS / "inflation.json").read_text())
    infl = {r["policy"]: r for r in inflation["rows"]}
    ident = json.loads((EXPERIMENTS / "identical_pvalue.json").read_text())
    cost = json.loads((EXPERIMENTS / "correction_cost.json").read_text())
    crows = {r["procedure"]: r for r in cost["rows"]}

    metrics = {
        "tests_total": int(suite.get("tests")),
        "coverage_line_pct": round(coverage["totals"]["percent_covered"]),
        "trials": inflation["trials"],
        "fpr_single_pct": infl["single"]["fpr_pct"],
        "fpr_weekly_pct": infl["weekly"]["fpr_pct"],
        "fpr_daily_pct": infl["daily"]["fpr_pct"],
        "daily_ci_low_pct": infl["daily"]["ci_low_pct"],
        "daily_ci_high_pct": infl["daily"]["ci_high_pct"],
        "holdout_ci_low_pct": cost["holdout_ci"][0],
        "holdout_ci_high_pct": cost["holdout_ci"][1],
        "early_wins": ident["daily_early_wins"],
        "median_stop_day": ident["median_stop_day"],
        "evaporated_pct": ident["evaporated_pct"],
        "median_stop_p": ident["median_stop_p"],
        "median_single_p": ident["median_single_win_p"],
        "z_star": cost["z_star"],
        "per_peek_alpha": cost["per_peek_alpha"],
        "holdout_fpr_pct": cost["holdout_fpr_pct"],
        "power_single_pct": crows["single pre-registered look"]["power_pct"],
        "power_naive_pct": crows["naive daily peeking"]["power_pct"],
        "power_corrected_pct": crows["corrected daily peeking"]["power_pct"],
        "power_cost_points": cost["power_cost_points"],
        "horizon_n_per_arm": cost["horizon_n_per_arm"],
        "fixed_horizon_n_80pct": cost["fixed_horizon_n_80pct"],
    }
    return {"metrics": metrics, "anchors": ANCHORS,
            "checked_documents": ["README.md", "docs/defense-guide.md"],
            "note": "every value is produced by running the suite and the experiments"}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--skip-tests", action="store_true")
    parser.add_argument("--skip-experiments", action="store_true")
    args = parser.parse_args()
    payload = collect(args.skip_tests, args.skip_experiments)
    OUT.write_text(json.dumps(payload, indent=1, sort_keys=True))
    print(f"wrote {OUT} with {len(payload['metrics'])} metrics")


if __name__ == "__main__":
    main()
