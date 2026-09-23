import numpy as np
import pytest

from analytics.experiments import (cuped_adjust, mean_difference_test, sample_ratio_mismatch,
                                   sample_size_two_proportions, two_proportion_test)


def test_sample_size_matches_textbook_value():
    # 10% baseline, detect +10% relative (10% -> 11%), alpha 0.05, power 0.8: ~14,750 per group
    assert 14_500 < sample_size_two_proportions(0.10, 0.10) < 15_000


def test_srm_flags_broken_split_but_not_a_fair_one():
    assert sample_ratio_mismatch(5000, 5050)["mismatch"] is False
    assert sample_ratio_mismatch(5000, 5600)["mismatch"] is True


def test_two_proportion_test_detects_real_lift():
    r = two_proportion_test(1000, 10_000, 1150, 10_000)
    assert r.significant and r.relative_lift == pytest.approx(0.15)
    assert r.ci_low > 0


def test_no_lift_is_not_significant():
    assert not two_proportion_test(1000, 10_000, 1010, 10_000).significant


def test_cuped_keeps_mean_and_cuts_variance():
    rng = np.random.default_rng(0)
    pre = rng.normal(100, 20, 5000)
    post = pre * 0.8 + rng.normal(0, 5, 5000)
    adjusted = cuped_adjust(post, pre)
    assert adjusted.mean() == pytest.approx(post.mean())
    assert adjusted.var() < post.var() * 0.2


def test_cuped_makes_a_small_effect_detectable():
    rng = np.random.default_rng(1)
    pre = rng.normal(100, 30, 4000)
    group = np.repeat([0, 1], 2000)
    post = pre + rng.normal(0, 10, 4000) + group * 1.0  # small true effect
    raw = mean_difference_test(post[group == 0], post[group == 1])
    adj = cuped_adjust(post, pre)
    cuped = mean_difference_test(adj[group == 0], adj[group == 1])
    assert cuped["p_value"] < raw["p_value"]
    assert cuped["significant"]
