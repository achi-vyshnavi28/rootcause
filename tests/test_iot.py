import numpy as np

from iot.kalman import KalmanTrend
from iot.sensor_stream import Machine, run


def test_kalman_recovers_level_and_slope_from_noisy_readings():
    rng = np.random.default_rng(0)
    kf = KalmanTrend(measurement_var=0.25)
    for t in range(300):
        level, slope = kf.step(1.0 + 0.02 * t + rng.normal(0, 0.5))
    assert abs(slope - 0.02) < 0.005
    assert abs(level - (1.0 + 0.02 * 299)) < 0.5


def test_steps_to_threshold():
    kf = KalmanTrend()
    kf.x = np.array([5.0, 0.1])
    assert kf.steps_to_threshold(8.0) == 30.0
    kf.x = np.array([5.0, -0.1])
    assert kf.steps_to_threshold(8.0) is None


def test_degrading_machine_is_warned_before_failure_and_healthy_ones_are_not():
    fleet = [Machine("healthy-1"), Machine("healthy-2"), Machine("wearing", wear_starts_at=100, wear_rate=0.05)]
    monitor, failed_at = run(fleet, steps=300)
    alerted = {a["machine_id"]: a for a in monitor.alerts}
    assert set(alerted) == {"wearing"}
    assert failed_at["wearing"] is not None
    assert alerted["wearing"]["at_step"] < failed_at["wearing"]  # warned in advance
