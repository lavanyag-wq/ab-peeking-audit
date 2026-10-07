"""Properties of the audit verdicts, the exact interval, and the calibration."""

import numpy as np
import pytest

from ab_peeking_audit.audit import (
    VERDICT_CONSISTENT,
    VERDICT_INCONCLUSIVE,
    VERDICT_INFLATED,
    audit_policy,
    clopper_pearson,
    critical_value,
    declared,
    peek_days,
)
from ab_peeking_audit.boundary import calibrate_boundary, power, stop_profile
from ab_peeking_audit.errors import UsageError
from ab_peeking_audit.simulate import Design

NULL = Design(28, 400, 0.05, 0.05)
LIFT = Design(28, 400, 0.05, 0.0575)


def test_single_policy_peeks_once_on_the_last_day():
    assert peek_days("single", 28) == [27]


def test_weekly_policy_peeks_every_seventh_day_and_the_horizon():
    assert peek_days("weekly", 28) == [6, 13, 20, 27]
    assert peek_days("weekly", 30) == [6, 13, 20, 27, 29]


def test_daily_policy_peeks_every_day():
    assert peek_days("daily", 5) == [0, 1, 2, 3, 4]


def test_an_unknown_policy_is_refused():
    with pytest.raises(UsageError, match="unknown policy"):
        peek_days("hourly", 28)


def test_the_critical_value_at_five_percent_is_the_familiar_1_96():
    assert critical_value(0.05) == pytest.approx(1.959964, abs=1e-5)


def test_alpha_outside_the_unit_interval_is_refused():
    with pytest.raises(UsageError, match="alpha"):
        critical_value(1.0)


def test_declared_refuses_peek_days_outside_the_matrix():
    z = np.zeros((3, 5))
    with pytest.raises(UsageError, match="out of range"):
        declared(z, [7], 1.96)


def test_more_peeks_can_only_grow_the_declared_set():
    z = np.abs(np.random.default_rng(0).normal(size=(500, 28)))
    daily = declared(z, peek_days("daily", 28), 1.96)
    single = declared(z, peek_days("single", 28), 1.96)
    assert (single <= daily).all()


def test_clopper_pearson_matches_a_known_value():
    lo, hi = clopper_pearson(5, 100)
    assert lo == pytest.approx(0.01643, abs=1e-4)
    assert hi == pytest.approx(0.11283, abs=1e-4)


def test_clopper_pearson_handles_the_zero_and_full_counts():
    lo, hi = clopper_pearson(0, 50)
    assert lo == 0.0 and 0 < hi < 0.1
    lo, hi = clopper_pearson(50, 50)
    assert hi == 1.0 and 0.9 < lo < 1.0


def test_clopper_pearson_refuses_invalid_counts():
    with pytest.raises(UsageError):
        clopper_pearson(5, 0)
    with pytest.raises(UsageError):
        clopper_pearson(6, 5)


def test_auditing_a_non_null_design_is_refused():
    with pytest.raises(UsageError, match="requires p_a == p_b"):
        audit_policy(LIFT, "daily", 0.05, 100, seed=7)


def test_the_single_look_procedure_is_consistent_with_its_alpha():
    result = audit_policy(NULL, "single", 0.05, 4000, seed=7)
    assert result.verdict == VERDICT_CONSISTENT
    assert result.ci_low <= 0.05 <= result.ci_high


def test_daily_peeking_is_called_inflated_with_the_interval_above_alpha():
    result = audit_policy(NULL, "daily", 0.05, 4000, seed=7)
    assert result.verdict == VERDICT_INFLATED
    assert result.ci_low > 0.05
    assert result.fpr > 0.2


def test_weekly_peeking_is_also_called_inflated():
    assert audit_policy(NULL, "weekly", 0.05, 4000, seed=7).verdict == VERDICT_INFLATED


def test_too_few_trials_yield_inconclusive_not_consistent():
    # 60 null trials cannot distinguish 5% from 10%; the verdict must say so.
    result = audit_policy(NULL, "single", 0.05, 60, seed=7)
    assert result.verdict == VERDICT_INCONCLUSIVE
    assert result.ci_low <= 0.05 and result.ci_high > 0.10


def test_the_fpr_equals_false_positives_over_trials():
    result = audit_policy(NULL, "weekly", 0.05, 500, seed=3)
    assert result.fpr == pytest.approx(result.false_positives / 500)


def test_calibration_requires_a_null_design_and_a_distinct_holdout_seed():
    with pytest.raises(UsageError, match="null design"):
        calibrate_boundary(LIFT, "daily", 0.05, 100, seed=1, holdout_seed=2)
    with pytest.raises(UsageError, match="holdout_seed"):
        calibrate_boundary(NULL, "daily", 0.05, 100, seed=1, holdout_seed=1)


def test_the_calibrated_boundary_exceeds_the_naive_critical_value():
    cal = calibrate_boundary(NULL, "daily", 0.05, 2000, seed=11, holdout_seed=12)
    assert cal.z_star > critical_value(0.05)
    assert 0.0 < cal.per_peek_alpha < 0.05


def test_the_calibrated_boundary_restores_alpha_on_held_out_nulls():
    cal = calibrate_boundary(NULL, "daily", 0.05, 4000, seed=11, holdout_seed=12)
    assert cal.holdout_ci_low <= 0.05
    assert cal.holdout_fpr < 0.08


def test_power_requires_a_real_effect():
    with pytest.raises(UsageError, match="p_a != p_b"):
        power(NULL, "single", 1.96, 100, seed=7)


def test_corrected_daily_peeking_costs_power_versus_a_single_look():
    # The uncomfortable number: honesty is not free, and the test pins its sign.
    p_single, *_ = power(LIFT, "single", critical_value(0.05), 2000, seed=21)
    cal_z = 2.731
    p_corr, *_ = power(LIFT, "daily", cal_z, 2000, seed=21)
    assert p_corr < p_single


def test_naive_daily_power_exceeds_single_look_because_it_cheats():
    p_single, *_ = power(LIFT, "single", critical_value(0.05), 2000, seed=21)
    p_naive, *_ = power(LIFT, "daily", critical_value(0.05), 2000, seed=21)
    assert p_naive > p_single


def test_stop_profile_reports_first_crossing_days_for_declaring_trials():
    z = np.array([[0.5, 2.5, 3.0], [0.1, 0.2, 0.3], [2.2, 0.1, 0.1]])
    days = stop_profile(z, [0, 1, 2], 1.96)
    assert days.tolist() == [1, 0]


def test_audit_results_carry_the_peek_count_for_the_policy():
    assert audit_policy(NULL, "weekly", 0.05, 200, seed=1).n_peeks == 4
    assert audit_policy(NULL, "single", 0.05, 200, seed=1).n_peeks == 1


def test_peek_days_refuses_a_nonpositive_horizon():
    with pytest.raises(UsageError, match="days"):
        peek_days("daily", 0)


def test_weekly_horizon_on_a_multiple_of_seven_is_not_double_counted():
    days = peek_days("weekly", 28)
    assert len(days) == len(set(days))


@pytest.mark.parametrize("alpha", [0.01, 0.05, 0.1])
def test_single_look_fpr_tracks_its_nominal_alpha(alpha):
    small = Design(7, 150, 0.05, 0.05)
    result = audit_policy(small, "single", alpha, 3000, seed=4)
    assert result.ci_low <= alpha * 1.6 and result.ci_high >= alpha * 0.5


@pytest.mark.parametrize("policy,expected_order", [("single", 0), ("weekly", 1),
                                                   ("daily", 2)])
def test_fpr_grows_with_peek_frequency(policy, expected_order):
    small = Design(14, 150, 0.05, 0.05)
    rates = {p: audit_policy(small, p, 0.05, 2500, seed=6).fpr
             for p in ("single", "weekly", "daily")}
    ordering = sorted(rates, key=rates.get)
    assert ordering.index(policy) == expected_order


def test_a_tighter_alpha_calibrates_a_higher_boundary():
    small = Design(10, 120, 0.05, 0.05)
    loose = calibrate_boundary(small, "daily", 0.10, 1500, seed=1, holdout_seed=2)
    tight = calibrate_boundary(small, "daily", 0.01, 1500, seed=1, holdout_seed=2)
    assert tight.z_star > loose.z_star


def test_stop_profile_is_empty_when_nothing_crosses():
    import numpy as np
    z = np.zeros((4, 3))
    assert stop_profile(z, [0, 1, 2], 1.96).size == 0
