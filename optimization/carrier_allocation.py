"""Decide how many parcels each carrier should take per region, as an integer program (OR-Tools CP-SAT).

Minimise  shipping cost + penalty x expected late parcels
subject to  every parcel is assigned, and no carrier exceeds its daily capacity.

Demand comes from real Olist order volumes per customer state; carrier costs, capacities and
on-time rates are assumptions (edit CARRIERS) representing the June 2018 incident: the main SP
carrier lost a third of its drivers.

    python -m optimization.carrier_allocation
"""

from dataclasses import dataclass

from ortools.sat.python import cp_model
from sqlalchemy import text

from backend.config import readonly_engine


@dataclass(frozen=True)
class Carrier:
    name: str
    capacity_per_day: int
    cost_per_parcel: dict[str, float]  # region -> BRL
    on_time_rate: dict[str, float]  # region -> probability


def solve(demand: dict[str, int], carriers: list[Carrier], late_penalty: float = 25.0) -> dict:
    model = cp_model.CpModel()
    x = {(c.name, r): model.NewIntVar(0, demand[r], f"x_{c.name}_{r}")
         for c in carriers for r in demand if r in c.cost_per_parcel}
    for r, d in demand.items():
        model.Add(sum(v for (cn, rr), v in x.items() if rr == r) == d)
    for c in carriers:
        model.Add(sum(v for (cn, _), v in x.items() if cn == c.name) <= c.capacity_per_day)
    # CP-SAT needs integers. Both terms are expressed in thousandths of a centavo:
    #   cost: centavos x 1000;  late: (late probability x 1000) x penalty in centavos.
    by_name = {c.name: c for c in carriers}
    cost = sum(v * int(round(100 * by_name[cn].cost_per_parcel[r])) for (cn, r), v in x.items())
    late = sum(v * int(round(1000 * (1 - by_name[cn].on_time_rate[r]))) for (cn, r), v in x.items())
    model.Minimize(cost * 1000 + late * int(round(late_penalty * 100)))
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = 10
    status = solver.Solve(model)
    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        return {"status": "infeasible", "reason": "total demand exceeds total carrier capacity"}
    plan = {f"{cn}->{r}": solver.Value(v) for (cn, r), v in x.items() if solver.Value(v)}
    exp_late = sum(solver.Value(v) * (1 - by_name[cn].on_time_rate[r]) for (cn, r), v in x.items())
    total_cost = sum(solver.Value(v) * by_name[cn].cost_per_parcel[r] for (cn, r), v in x.items())
    return {"status": "optimal" if status == cp_model.OPTIMAL else "feasible", "plan": plan,
            "expected_late_parcels": round(exp_late, 1), "expected_late_rate": round(exp_late / sum(demand.values()), 4),
            "shipping_cost_brl": round(total_cost, 2)}


def daily_demand(month_start: str = "2018-06-01", month_end: str = "2018-07-01") -> dict[str, int]:
    """Average daily orders per region (SP, RJ, MG, other) from real Olist data."""
    sql = """
        SELECT CASE WHEN c.customer_state IN ('SP', 'RJ', 'MG') THEN c.customer_state ELSE 'other' END AS region,
               COUNT(*) / 30.0 AS per_day
        FROM olist.orders o JOIN olist.customers c USING (customer_id)
        WHERE o.order_purchase_timestamp >= :s AND o.order_purchase_timestamp < :e GROUP BY 1"""
    with readonly_engine().connect() as conn:
        rows = conn.execute(text(sql), {"s": month_start, "e": month_end}).all()
    return {r: int(round(float(v))) for r, v in rows}


REGIONS = ("SP", "RJ", "MG", "other")
INCIDENT_CARRIERS = [
    Carrier("main_carrier", capacity_per_day=120,  # was ~180 before losing a third of its drivers
            cost_per_parcel={"SP": 9.0, "RJ": 14.0, "MG": 13.0, "other": 18.0},
            on_time_rate={"SP": 0.70, "RJ": 0.92, "MG": 0.93, "other": 0.90}),
    Carrier("national_post", capacity_per_day=400,
            cost_per_parcel={"SP": 12.0, "RJ": 15.0, "MG": 15.0, "other": 17.0},
            on_time_rate={"SP": 0.88, "RJ": 0.88, "MG": 0.88, "other": 0.86}),
    Carrier("new_sp_courier", capacity_per_day=80,  # the second carrier from the incident report
            cost_per_parcel={"SP": 11.0},
            on_time_rate={"SP": 0.95}),
]


def main() -> None:
    demand = daily_demand()
    print("Daily demand (real Olist, June 2018):", demand)
    for label, carriers in [("without new SP courier", INCIDENT_CARRIERS[:2]), ("with new SP courier", INCIDENT_CARRIERS)]:
        print(f"\n{label}:", solve(demand, carriers))


if __name__ == "__main__":
    main()
