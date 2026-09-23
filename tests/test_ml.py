import numpy as np
import pandas as pd

from ml.anomaly import detect
from ml.forecast import holt_winters, mape, seasonal_naive


def _weekly_series(days: int = 180, seed: int = 0) -> pd.Series:
    rng = np.random.default_rng(seed)
    idx = pd.date_range("2018-01-01", periods=days, freq="D")
    weekly = np.tile([120, 110, 105, 100, 95, 80, 70], days // 7 + 1)[:days]
    return pd.Series(weekly + np.linspace(0, 20, days) + rng.normal(0, 3, days), index=idx)


def test_anomaly_detector_finds_planted_spike_and_ignores_weekly_pattern():
    s = _weekly_series()
    s.iloc[100] += 80
    found = detect(s)
    assert found.index[0] == s.index[100]
    assert len(found) == 1


def test_seasonal_naive_repeats_last_week():
    s = _weekly_series()
    assert np.allclose(seasonal_naive(s, 7), s.iloc[-7:].to_numpy())


def test_holt_winters_beats_a_flat_guess_on_seasonal_data():
    s = _weekly_series()
    train, test = s.iloc[:-28], s.iloc[-28:].to_numpy()
    flat = np.full(28, train.mean())
    assert mape(test, holt_winters(train, 28)) < mape(test, flat)
