"""Last-mile vehicle routing for one day of Sao Paulo deliveries (OR-Tools), on real Olist locations.

Customer coordinates come from the Olist geolocation table (zip-code prefix -> lat/lng).
Compares OR-Tools' optimised routes with a naive plan (vans take stops in the order they arrived).

    python -m optimization.routing
"""

import math

import numpy as np
from ortools.constraint_solver import pywrapcp, routing_enums_pb2
from sqlalchemy import text

from backend.config import readonly_engine

DEPOT = (-23.55, -46.63)  # central Sao Paulo


def haversine_km(a: tuple[float, float], b: tuple[float, float]) -> float:
    lat1, lon1, lat2, lon2 = map(math.radians, (*a, *b))
    h = math.sin((lat2 - lat1) / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin((lon2 - lon1) / 2) ** 2
    return 2 * 6371 * math.asin(math.sqrt(h))


def distance_matrix(points: list[tuple[float, float]]) -> np.ndarray:
    n = len(points)
    return np.array([[haversine_km(points[i], points[j]) for j in range(n)] for i in range(n)])


def solve_vrp(points: list[tuple[float, float]], vehicles: int, capacity: int, time_limit_s: int = 10) -> dict:
    """points[0] is the depot. Every other point is one parcel. Distances in metres for the solver."""
    dist = (distance_matrix(points) * 1000).round().astype(int)
    manager = pywrapcp.RoutingIndexManager(len(points), vehicles, 0)
    routing = pywrapcp.RoutingModel(manager)
    transit = routing.RegisterTransitCallback(lambda i, j: int(dist[manager.IndexToNode(i)][manager.IndexToNode(j)]))
    routing.SetArcCostEvaluatorOfAllVehicles(transit)
    demand = routing.RegisterUnaryTransitCallback(lambda i: 0 if manager.IndexToNode(i) == 0 else 1)
    routing.AddDimensionWithVehicleCapacity(demand, 0, [capacity] * vehicles, True, "load")
    params = pywrapcp.DefaultRoutingSearchParameters()
    params.first_solution_strategy = routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC
    params.local_search_metaheuristic = routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH
    params.time_limit.seconds = time_limit_s
    solution = routing.SolveWithParameters(params)
    if solution is None:
        return {"status": "no solution"}
    routes, total = [], 0
    for v in range(vehicles):
        idx, route = routing.Start(v), []
        while not routing.IsEnd(idx):
            route.append(manager.IndexToNode(idx))
            nxt = solution.Value(routing.NextVar(idx))
            total += routing.GetArcCostForVehicle(idx, nxt, v)
            idx = nxt
        routes.append(route[1:])
    return {"status": "ok", "total_km": round(total / 1000, 1), "routes": [r for r in routes if r]}


def naive_km(points: list[tuple[float, float]], vehicles: int, capacity: int) -> float:
    """Stops split among vans in arrival order, each van visiting them in that order."""
    dist, total = distance_matrix(points), 0.0
    stops = list(range(1, len(points)))
    for v in range(vehicles):
        chunk = stops[v * capacity:(v + 1) * capacity]
        if chunk:
            path = [0, *chunk, 0]
            total += sum(dist[a][b] for a, b in zip(path, path[1:]))
    return round(total, 1)


def sao_paulo_stops(day: str = "2018-06-12", limit: int = 60) -> list[tuple[float, float]]:
    sql = """
        SELECT AVG(g.geolocation_lat) AS lat, AVG(g.geolocation_lng) AS lng
        FROM olist.orders o JOIN olist.customers c USING (customer_id)
        JOIN olist.geolocation g ON g.geolocation_zip_code_prefix = c.customer_zip_code_prefix
        WHERE c.customer_city = 'sao paulo' AND o.order_purchase_timestamp::date = :d
        GROUP BY o.order_id ORDER BY MIN(o.order_purchase_timestamp) LIMIT :n"""
    with readonly_engine().connect() as conn:
        rows = conn.execute(text(sql), {"d": day, "n": limit}).all()
    return [(float(a), float(b)) for a, b in rows if -24.1 < a < -23.3 and -47.0 < b < -46.3]


def main() -> None:
    stops = sao_paulo_stops()
    points, vehicles = [DEPOT, *stops], 4
    capacity = math.ceil(len(stops) / vehicles)
    result = solve_vrp(points, vehicles, capacity)
    naive = naive_km(points, vehicles, capacity)
    print(f"{len(stops)} real Sao Paulo stops, {vehicles} vans of capacity {capacity}")
    print(f"naive plan: {naive} km   optimised: {result['total_km']} km   "
          f"saving: {100 * (1 - result['total_km'] / naive):.0f}%")


if __name__ == "__main__":
    main()
