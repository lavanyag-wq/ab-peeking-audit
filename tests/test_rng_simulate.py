"""Properties of the PRNG and the simulator, including the statsmodels pin."""

import numpy as np
import pytest
from scipy.stats import norm
from statsmodels.stats.proportion import proportions_ztest

from ab_peeking_audit.errors import UsageError
from ab_peeking_audit.rng import bernoulli_matrix, uniforms
from ab_peeking_audit.simulate import Design, cumulative_counts, pooled_z, z_matrix


def test_the_same_seed_and_counters_reproduce_identical_uniforms():
    assert np.array_equal(uniforms(7, 0, 1000), uniforms(7, 0, 1000))


def test_draw_i_is_a_pure_function_of_seed_and_counter():
    # Counter-based means any slice equals the same slice of a larger request.
    assert np.array_equal(uniforms(7, 500, 100), uniforms(7, 0, 1000)[500:600])


def test_different_seeds_produce_different_streams():
    assert not np.array_equal(uniforms(7, 0, 100), uniforms(8, 0, 100))


def test_uniforms_lie_in_the_half_open_unit_interval():
    u = uniforms(3, 0, 100000)
    assert u.min() >= 0.0 and u.max() < 1.0


def test_uniform_mean_sits_near_one_half():
    assert abs(uniforms(5, 0, 1_000_000).mean() - 0.5) < 0.002


def test_a_known_draw_is_pinned_so_a_silent_prng_change_fails_loudly():
    # If this value ever moves, every published number in the repository
    # changes with it; the pin makes that a red build instead of a surprise.
    assert uniforms(7, 0, 1)[0] == pytest.approx(0.7215081806049702, abs=1e-15)


def test_negative_counts_and_seeds_are_refused():
    with pytest.raises(UsageError):
        uniforms(7, -1, 10)
    with pytest.raises(UsageError):
        uniforms(-1, 0, 10)


def test_bernoulli_matrix_respects_its_shape_and_probability():
    m = bernoulli_matrix(7, 0, 200, 500, 0.3)
    assert m.shape == (200, 500)
    assert set(np.unique(m)) <= {0, 1}
    assert abs(m.mean() - 0.3) < 0.01


def test_a_probability_outside_the_unit_interval_is_refused():
    with pytest.raises(UsageError, match="p must be"):
        bernoulli_matrix(7, 0, 2, 2, 1.5)


def test_design_validates_days_subjects_and_rates():
    with pytest.raises(UsageError):
        Design(0, 400, 0.05, 0.05)
    with pytest.raises(UsageError):
        Design(28, 0, 0.05, 0.05)
    with pytest.raises(UsageError):
        Design(28, 400, 0.0, 0.05)


def test_cumulative_counts_are_nondecreasing_and_bounded():
    design = Design(10, 50, 0.1, 0.1)
    a, b = cumulative_counts(design, 20, seed=7)
    assert (np.diff(a, axis=1) >= 0).all() and (np.diff(b, axis=1) >= 0).all()
    nobs = (np.arange(10) + 1) * 50
    assert (a <= nobs[None, :]).all() and (b <= nobs[None, :]).all()


def test_the_simulation_is_deterministic_for_a_seed():
    design = Design(5, 30, 0.2, 0.2)
    assert all(np.array_equal(x, y) for x, y in
               zip(cumulative_counts(design, 8, 7), cumulative_counts(design, 8, 7),
                   strict=True))


def test_arms_with_different_rates_separate_in_the_mean():
    design = Design(10, 200, 0.05, 0.20)
    a, b = cumulative_counts(design, 200, seed=7)
    assert b[:, -1].mean() > a[:, -1].mean() * 2


def test_trials_below_one_are_refused():
    with pytest.raises(UsageError, match="trials"):
        cumulative_counts(Design(5, 30, 0.1, 0.1), 0, seed=7)


def test_pooled_z_matches_statsmodels_proportions_ztest_on_a_grid():
    # The fast engine and the reference library must agree exactly, or every
    # Monte Carlo figure is about a different test than the one teams run.
    nobs = 400
    for conv_a in (0, 3, 17, 50, 200, 399):
        for conv_b in (1, 5, 40, 180, 400):
            stat, _p = proportions_ztest([conv_a, conv_b], [nobs, nobs])
            ours = pooled_z(np.array([conv_a]), np.array([conv_b]),
                            np.array([nobs]))[0]
            assert ours == pytest.approx(float(stat), abs=1e-12)


def test_pooled_z_is_zero_when_the_pooled_rate_is_degenerate():
    assert pooled_z(np.array([0]), np.array([0]), np.array([100]))[0] == 0.0
    assert pooled_z(np.array([100]), np.array([100]), np.array([100]))[0] == 0.0


def test_z_matrix_shape_is_trials_by_days():
    assert z_matrix(Design(6, 40, 0.1, 0.1), 15, seed=7).shape == (15, 6)


def test_z_matrix_is_nonnegative_because_the_test_is_two_sided():
    assert (z_matrix(Design(6, 40, 0.1, 0.1), 15, seed=7) >= 0).all()


def test_single_look_fpr_sits_near_alpha_as_a_calibration_check():
    z = z_matrix(Design(14, 200, 0.05, 0.05), 3000, seed=9)
    fpr = float((z[:, -1] >= norm.ppf(0.975)).mean())
    assert 0.03 < fpr < 0.07
