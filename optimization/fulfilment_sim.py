"""Discrete-event simulation (SimPy) of last-mile delivery, to test a fix BEFORE rolling it out.

Parcels arrive every day (Poisson, rate from real Olist SP volume). Drivers deliver a fixed number
per day; parcels not delivered wait in a backlog. A parcel is late if delivered after its promised day.
Scenarios: normal staffing, the June incident (a third of drivers gone), and the incident plus
a second carrier starting on a given day.

    python -m optimization.fulfilment_sim
"""

from collections import deque
from dataclasses import dataclass

import numpy as np
import simpy


@dataclass
class Scenario:
    name: str
    drivers: int
    parcels_per_driver: int = 12
    drivers_lost_from_day: int | None = None
    drivers_lost: int = 0
    extra_drivers_from_day: int | None = None
    extra_drivers: int = 0


def simulate(s: Scenario, arrivals_per_day: float, days: int = 60, promise_days: int = 3, seed: int = 0) -> dict:
    env = simpy.Environment()
    rng = np.random.default_rng(seed)
    backlog: deque[int] = deque()  # promised-by day of each waiting parcel
    delivered, late, backlog_sizes = 0, 0, []

    def drivers_on(day: int) -> int:
        n = s.drivers
        if s.drivers_lost_from_day is not None and day >= s.drivers_lost_from_day:
            n -= s.drivers_lost
        if s.extra_drivers_from_day is not None and day >= s.extra_drivers_from_day:
            n += s.extra_drivers
        return max(n, 0)

    def day_process():
        nonlocal delivered, late
        while True:
            day = int(env.now)
            for _ in range(rng.poisson(arrivals_per_day)):
                backlog.append(day + promise_days)
            for _ in range(min(len(backlog), drivers_on(day) * s.parcels_per_driver)):
                promised = backlog.popleft()  # first in, first out
                delivered += 1
                late += day > promised
            backlog_sizes.append(len(backlog))
            yield env.timeout(1)

    env.process(day_process())
    env.run(until=days)
    return {"scenario": s.name, "delivered": delivered, "late_rate": round(late / delivered, 4) if delivered else None,
            "final_backlog": backlog_sizes[-1], "max_backlog": max(backlog_sizes)}


def scenarios(sp_parcels_per_day: float) -> list[Scenario]:
    drivers = int(np.ceil(sp_parcels_per_day / 12 * 1.1))  # 10% headroom in normal times
    lost = drivers // 3
    return [
        Scenario("normal staffing", drivers),
        Scenario("incident: a third of drivers lost on day 10", drivers, drivers_lost_from_day=10, drivers_lost=lost),
        Scenario("incident + second carrier from day 20", drivers, drivers_lost_from_day=10, drivers_lost=lost,
                 extra_drivers_from_day=20, extra_drivers=lost),
        Scenario("incident + second carrier from day 14", drivers, drivers_lost_from_day=10, drivers_lost=lost,
                 extra_drivers_from_day=14, extra_drivers=lost),
    ]


def main() -> None:
    from optimization.carrier_allocation import daily_demand

    sp = daily_demand()["SP"]
    print(f"SP parcels per day (real Olist, June 2018): {sp}")
    for sc in scenarios(sp):
        print(simulate(sc, sp))


if __name__ == "__main__":
    main()
