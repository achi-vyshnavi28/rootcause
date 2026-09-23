import math

from optimization.carrier_allocation import Carrier, solve
from optimization.fulfilment_sim import Scenario, simulate
from optimization.routing import haversine_km, naive_km, solve_vrp

CHEAP_LATE = Carrier("cheap", 100, {"A": 5.0, "B": 5.0}, {"A": 0.5, "B": 0.5})
PRICEY_ONTIME = Carrier("pricey", 100, {"A": 8.0, "B": 8.0}, {"A": 0.99, "B": 0.99})


def test_allocation_respects_demand_and_capacity():
    r = solve({"A": 60, "B": 80}, [CHEAP_LATE, PRICEY_ONTIME])
    assert r["status"] == "optimal"
    assert sum(r["plan"].values()) == 140
    assert sum(v for k, v in r["plan"].items() if k.startswith("cheap")) <= 100


def test_high_late_penalty_shifts_volume_to_reliable_carrier():
    cheap = solve({"A": 50}, [CHEAP_LATE, PRICEY_ONTIME], late_penalty=0.1)
    careful = solve({"A": 50}, [CHEAP_LATE, PRICEY_ONTIME], late_penalty=100)
    assert cheap["plan"].get("cheap->A", 0) == 50
    assert careful["plan"].get("pricey->A", 0) == 50


def test_infeasible_when_demand_exceeds_capacity():
    assert solve({"A": 500}, [CHEAP_LATE])["status"] == "infeasible"


def test_losing_drivers_raises_late_rate_and_second_carrier_fixes_it():
    base = dict(drivers=10, parcels_per_driver=10)
    normal = simulate(Scenario("n", **base), arrivals_per_day=90)
    incident = simulate(Scenario("i", **base, drivers_lost_from_day=5, drivers_lost=4), arrivals_per_day=90)
    fixed = simulate(Scenario("f", **base, drivers_lost_from_day=5, drivers_lost=4,
                              extra_drivers_from_day=10, extra_drivers=4), arrivals_per_day=90)
    assert normal["late_rate"] < 0.02
    assert incident["late_rate"] > 0.3
    assert fixed["late_rate"] < incident["late_rate"]


def test_haversine_known_distance():
    # Sao Paulo -> Rio de Janeiro is ~360 km
    assert 350 < haversine_km((-23.55, -46.63), (-22.91, -43.17)) < 370


def test_vrp_beats_naive_on_scattered_points():
    pts = [(-23.55, -46.63)] + [(-23.55 + 0.05 * math.sin(i * 2.4), -46.63 + 0.05 * math.cos(i * 3.7)) for i in range(16)]
    r = solve_vrp(pts, vehicles=2, capacity=8, time_limit_s=3)
    assert r["status"] == "ok" and sorted(i for route in r["routes"] for i in route) == list(range(1, 17))
    assert r["total_km"] <= naive_km(pts, 2, 8)
