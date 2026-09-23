"""Simulated machines streaming sensor readings, and a monitor that warns before they fail.

Transport is pluggable: an in-memory bus (default, used in tests) or a real MQTT broker
(set MQTT_HOST, e.g. a local Mosquitto or a free cloud broker). Topic: factory/<machine>/vibration

    python -m iot.sensor_stream                # in-memory demo
    MQTT_HOST=localhost python -m iot.sensor_stream
"""

import json
import os
from collections import defaultdict
from dataclasses import dataclass
from typing import Callable

import numpy as np

from iot.kalman import KalmanTrend

FAILURE_LEVEL = 8.0  # vibration (mm/s) at which the machine must be stopped
WARN_WITHIN_STEPS = 48  # warn when failure is predicted within 48 readings (e.g. hours)


@dataclass
class Machine:
    machine_id: str
    base: float = 2.0
    wear_starts_at: int | None = None  # step when degradation begins (None = healthy)
    wear_rate: float = 0.05
    noise: float = 0.4

    def true_level(self, t: int) -> float:
        wear = max(0, t - self.wear_starts_at) * self.wear_rate if self.wear_starts_at is not None else 0.0
        return self.base + wear

    def reading(self, t: int, rng: np.random.Generator) -> float:
        return self.true_level(t) + rng.normal(0, self.noise)


class InMemoryBus:
    def __init__(self):
        self.subscribers: list[Callable[[str, bytes], None]] = []

    def publish(self, topic: str, payload: bytes) -> None:
        for callback in self.subscribers:
            callback(topic, payload)

    def subscribe(self, callback: Callable[[str, bytes], None]) -> None:
        self.subscribers.append(callback)


class MqttBus:
    """Same interface over a real broker (paho-mqtt)."""

    def __init__(self, host: str, port: int = 1883):
        import paho.mqtt.client as mqtt

        self.client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
        self.client.connect(host, port)
        self.client.loop_start()

    def publish(self, topic: str, payload: bytes) -> None:
        self.client.publish(topic, payload, qos=1)

    def subscribe(self, callback: Callable[[str, bytes], None]) -> None:
        self.client.on_message = lambda _c, _u, msg: callback(msg.topic, msg.payload)
        self.client.subscribe("factory/+/vibration", qos=1)


class Monitor:
    """One Kalman filter per machine; raises an alert when predicted time-to-failure is short."""

    def __init__(self):
        self.filters: dict[str, KalmanTrend] = defaultdict(KalmanTrend)
        self.alerts: list[dict] = []
        self.alerted: set[str] = set()

    def on_message(self, topic: str, payload: bytes) -> None:
        msg = json.loads(payload)
        kf = self.filters[msg["machine_id"]]
        level, slope = kf.step(msg["value"])
        eta = kf.steps_to_threshold(FAILURE_LEVEL)
        if eta is not None and eta <= WARN_WITHIN_STEPS and msg["machine_id"] not in self.alerted and msg["t"] > 10:
            self.alerted.add(msg["machine_id"])
            self.alerts.append({"machine_id": msg["machine_id"], "at_step": msg["t"], "smoothed_level": round(level, 2),
                                "slope_per_step": round(slope, 4), "predicted_steps_to_failure": round(eta, 1)})


def run(machines: list[Machine], steps: int, bus=None, seed: int = 0) -> tuple[Monitor, dict[str, int | None]]:
    """Stream all machines; returns the monitor and the step each machine actually crossed FAILURE_LEVEL."""
    bus = bus or InMemoryBus()
    monitor = Monitor()
    bus.subscribe(monitor.on_message)
    rng = np.random.default_rng(seed)
    failed_at: dict[str, int | None] = {m.machine_id: None for m in machines}
    for t in range(steps):
        for m in machines:
            if failed_at[m.machine_id] is None and m.true_level(t) >= FAILURE_LEVEL:
                failed_at[m.machine_id] = t
            bus.publish(f"factory/{m.machine_id}/vibration",
                        json.dumps({"machine_id": m.machine_id, "t": t, "value": round(m.reading(t, rng), 3)}).encode())
    return monitor, failed_at


def main() -> None:
    fleet = [Machine("press-1"), Machine("press-2", wear_starts_at=150), Machine("cnc-7", wear_starts_at=60, wear_rate=0.03),
             Machine("pump-3")]
    bus = MqttBus(os.environ["MQTT_HOST"]) if os.getenv("MQTT_HOST") else None
    monitor, failed_at = run(fleet, steps=400, bus=bus)
    for a in monitor.alerts:
        lead = failed_at[a["machine_id"]] - a["at_step"] if failed_at[a["machine_id"]] is not None else None
        print({**a, "actual_failure_step": failed_at[a["machine_id"]], "warning_lead_steps": lead})
    healthy = [m.machine_id for m in fleet if m.wear_starts_at is None]
    print("false alarms on healthy machines:", [a for a in monitor.alerts if a["machine_id"] in healthy])


if __name__ == "__main__":
    main()
