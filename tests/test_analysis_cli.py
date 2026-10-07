"""The statsmodels reference path, the replay, and the CLI exit contract."""

import pytest

from ab_peeking_audit.analysis import fixed_horizon_n, reference_p_value, replay
from ab_peeking_audit.cli import main
from ab_peeking_audit.errors import (
    EXIT_CONSISTENT,
    EXIT_ERROR,
    EXIT_INCONCLUSIVE,
    EXIT_INFLATED,
    UsageError,
)
from ab_peeking_audit.simulate import Design


def test_reference_p_is_one_for_a_degenerate_pooled_rate():
    assert reference_p_value(0, 0, 100) == 1.0
    assert reference_p_value(100, 100, 100) == 1.0


def test_reference_p_is_small_for_a_large_separation():
    assert reference_p_value(80, 20, 400) < 1e-6


def test_reference_p_refuses_a_nonpositive_sample():
    with pytest.raises(UsageError, match="nobs"):
        reference_p_value(1, 1, 0)


def test_fixed_horizon_n_matches_the_textbook_order_of_magnitude():
    n = fixed_horizon_n(0.05, 0.0575, alpha=0.05, power_target=0.8)
    assert 9000 < n < 15000


def test_fixed_horizon_n_for_a_zero_effect_is_refused():
    with pytest.raises(UsageError, match="zero effect"):
        fixed_horizon_n(0.05, 0.05)


def test_a_replay_records_every_scheduled_peek():
    r = replay(Design(14, 100, 0.05, 0.05), "weekly", seed=3, trial=0,
               alpha=0.05, z_star=2.731)
    assert [rec.day for rec in r.records] == [7, 14]


def test_replay_refuses_a_trial_index_out_of_range():
    with pytest.raises(UsageError, match="out of range"):
        replay(Design(7, 50, 0.05, 0.05), "daily", seed=3, trial=2,
               alpha=0.05, z_star=2.731, trials=2)


def test_the_corrected_rule_never_stops_before_the_naive_rule():
    # z* > 1.96, so corrected stopping implies naive stopping at that peek.
    for seed in range(6):
        r = replay(Design(21, 300, 0.05, 0.05), "daily", seed=seed, trial=0,
                   alpha=0.05, z_star=2.731)
        naive, corrected = r.naive_stop_day, r.corrected_stop_day
        if corrected is not None:
            assert naive is not None and naive <= corrected


def test_the_final_p_is_the_last_peek_p():
    r = replay(Design(10, 100, 0.05, 0.05), "daily", seed=5, trial=0,
               alpha=0.05, z_star=2.731)
    assert r.final_p == r.records[-1].p_value


# CLI ---------------------------------------------------------------------

FAST = ["--days", "14", "--per-day", "150"]


def test_cli_single_look_audit_exits_consistent(capsys):
    code = main(["audit", "--policy", "single", "--trials", "1500", *FAST])
    assert code == EXIT_CONSISTENT
    assert "verdict: CONSISTENT" in capsys.readouterr().out


def test_cli_daily_audit_exits_inflated(capsys):
    code = main(["audit", "--policy", "daily", "--trials", "1500", *FAST])
    assert code == EXIT_INFLATED
    out = capsys.readouterr().out
    assert "verdict: INFLATED" in out
    assert "exact 95% interval" in out


def test_cli_tiny_trial_count_exits_inconclusive(capsys):
    code = main(["audit", "--policy", "single", "--trials", "60", *FAST])
    assert code == EXIT_INCONCLUSIVE
    assert "INCONCLUSIVE" in capsys.readouterr().out


def test_cli_audit_of_an_unknown_policy_exits_error(capsys):
    assert main(["audit", "--policy", "hourly", "--trials", "100", *FAST]) == EXIT_ERROR
    assert "error:" in capsys.readouterr().err


def test_cli_boundary_prints_z_star_and_held_out_rate(capsys):
    code = main(["boundary", "--policy", "daily", "--trials", "1500",
                 "--seed", "11", "--holdout-seed", "12", *FAST])
    assert code == EXIT_CONSISTENT
    out = capsys.readouterr().out
    assert "calibrated z*" in out and "held-out false positive rate" in out


def test_cli_boundary_with_equal_seeds_exits_error(capsys):
    code = main(["boundary", "--trials", "200", "--seed", "5",
                 "--holdout-seed", "5", *FAST])
    assert code == EXIT_ERROR


def test_cli_replay_prints_the_log_and_the_forgetting_line(capsys):
    code = main(["replay", "--policy", "weekly", "--seed", "42", *FAST])
    assert code == EXIT_CONSISTENT
    out = capsys.readouterr().out
    assert "naive  corrected" in out
    assert "all a report keeps" in out


def test_cli_samplesize_reports_a_per_arm_n(capsys):
    code = main(["samplesize", "--lift", "0.0075"])
    assert code == EXIT_CONSISTENT
    assert "per-arm n" in capsys.readouterr().out


def test_a_quiet_null_replay_declares_nothing_under_either_rule():
    r = replay(Design(7, 50, 0.05, 0.05), "single", seed=1, trial=0,
               alpha=0.05, z_star=2.731)
    assert r.naive_stop_day is None and r.corrected_stop_day is None


def test_a_strong_effect_replay_stops_under_both_rules():
    r = replay(Design(14, 400, 0.05, 0.15), "daily", seed=2, trial=0,
               alpha=0.05, z_star=2.731)
    assert r.naive_stop_day is not None and r.corrected_stop_day is not None


def test_cli_replay_with_a_lift_shows_an_effect_run(capsys):
    code = main(["replay", "--policy", "daily", "--seed", "2", "--lift", "0.1",
                 "--days", "10", "--per-day", "300"])
    assert code == EXIT_CONSISTENT
    assert "declares on day" in capsys.readouterr().out
