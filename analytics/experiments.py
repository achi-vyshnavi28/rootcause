"""A/B test toolkit: sample size, sample-ratio-mismatch check, significance tests, CUPED.

RootCause's reports end with a "suggested experiment"; these functions size and read that experiment.
"""

import math
from dataclasses import dataclass

import numpy as np
from scipy import stats


def sample_size_two_proportions(baseline: float, min_detectable_lift: float, alpha: float = 0.05, power: float = 0.8) -> int:
    """Users needed PER GROUP to detect a relative lift in a conversion-style rate (two-sided test)."""
    p1 = baseline
    p2 = baseline * (1 + min_detectable_lift)
    z_a, z_b = stats.norm.ppf(1 - alpha / 2), stats.norm.ppf(power)
    p_bar = (p1 + p2) / 2
    n = (z_a * math.sqrt(2 * p_bar * (1 - p_bar)) + z_b * math.sqrt(p1 * (1 - p1) + p2 * (1 - p2))) ** 2 / (p2 - p1) ** 2
    return math.ceil(n)


def sample_ratio_mismatch(n_control: int, n_treatment: int, expected_share: float = 0.5, threshold: float = 0.001) -> dict:
    """Chi-square test that the split matches the design. A tiny p-value means the experiment is broken: don't read it."""
    total = n_control + n_treatment
    expected = [total * (1 - expected_share), total * expected_share]
    chi2, p = stats.chisquare([n_control, n_treatment], expected)
    return {"chi2": float(chi2), "p_value": float(p), "mismatch": bool(p < threshold)}


@dataclass
class ProportionResult:
    rate_control: float
    rate_treatment: float
    absolute_lift: float
    relative_lift: float
    p_value: float
    ci_low: float
    ci_high: float
    significant: bool


def two_proportion_test(conv_c: int, n_c: int, conv_t: int, n_t: int, alpha: float = 0.05) -> ProportionResult:
    p_c, p_t = conv_c / n_c, conv_t / n_t
    pooled = (conv_c + conv_t) / (n_c + n_t)
    se_pooled = math.sqrt(pooled * (1 - pooled) * (1 / n_c + 1 / n_t))
    z = (p_t - p_c) / se_pooled if se_pooled else 0.0
    p_value = 2 * (1 - stats.norm.cdf(abs(z)))
    se = math.sqrt(p_c * (1 - p_c) / n_c + p_t * (1 - p_t) / n_t)
    margin = stats.norm.ppf(1 - alpha / 2) * se
    diff = p_t - p_c
    return ProportionResult(p_c, p_t, diff, diff / p_c if p_c else float("nan"), float(p_value),
                            diff - margin, diff + margin, p_value < alpha)


def cuped_adjust(metric: np.ndarray, pre_metric: np.ndarray) -> np.ndarray:
    """CUPED: remove the part of the metric explained by the same user's pre-experiment value.

    Same mean, lower variance, so the same experiment reaches significance with fewer users.
    """
    theta = np.cov(metric, pre_metric, ddof=1)[0, 1] / np.var(pre_metric, ddof=1)
    return metric - theta * (pre_metric - pre_metric.mean())


def mean_difference_test(control: np.ndarray, treatment: np.ndarray, alpha: float = 0.05) -> dict:
    t, p = stats.ttest_ind(treatment, control, equal_var=False)  # Welch's t-test
    diff = float(treatment.mean() - control.mean())
    se = math.sqrt(control.var(ddof=1) / len(control) + treatment.var(ddof=1) / len(treatment))
    margin = stats.norm.ppf(1 - alpha / 2) * se
    return {"difference": diff, "p_value": float(p), "ci": (diff - margin, diff + margin), "significant": bool(p < alpha)}
