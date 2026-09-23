"""Kalman filter from scratch (numpy only), tracking a sensor's level AND its rate of change.

State x = [level, slope]. Each step:
  predict:  x = F x,          P = F P F^T + Q      (constant-velocity model)
  update:   K = P H^T (H P H^T + R)^-1
            x = x + K (z - H x),  P = (I - K H) P
Knowing the slope lets us estimate WHEN the level will cross a failure threshold.
"""

from dataclasses import dataclass, field

import numpy as np


@dataclass
class KalmanTrend:
    process_var: float = 1e-5  # how much the true level/slope may wander per step (tuned: accurate slope, still ~50 steps of warning)
    measurement_var: float = 0.25  # sensor noise variance
    x: np.ndarray = field(default_factory=lambda: np.zeros(2))
    P: np.ndarray = field(default_factory=lambda: np.eye(2) * 1000.0)  # very uncertain start
    initialised: bool = False

    F = np.array([[1.0, 1.0], [0.0, 1.0]])
    H = np.array([[1.0, 0.0]])

    def step(self, z: float) -> tuple[float, float]:
        if not self.initialised:
            self.x, self.initialised = np.array([z, 0.0]), True
            return float(self.x[0]), float(self.x[1])
        Q = self.process_var * np.array([[0.25, 0.5], [0.5, 1.0]])
        self.x = self.F @ self.x
        self.P = self.F @ self.P @ self.F.T + Q
        S = self.H @ self.P @ self.H.T + self.measurement_var
        K = self.P @ self.H.T / S
        self.x = self.x + (K * (z - (self.H @ self.x)[0])).ravel()
        self.P = (np.eye(2) - K @ self.H) @ self.P
        return float(self.x[0]), float(self.x[1])

    def steps_to_threshold(self, threshold: float) -> float | None:
        """Estimated steps until the level reaches `threshold` at the current slope (None if not heading there)."""
        level, slope = self.x
        if slope <= 0 or level >= threshold:
            return 0.0 if level >= threshold else None
        return float((threshold - level) / slope)
