"""A tiny synthetic Olist-shaped database in DuckDB, with an anomaly we control.

Lets the whole agent run end-to-end in tests and CI without PostgreSQL or an LLM key.
"""

import random
from datetime import datetime, timedelta

import duckdb
import pandas as pd

from backend.db.executor import QueryResult

STATES = ["SP"] * 5 + ["RJ"] * 3 + ["MG"] * 2
SELLERS = {"s1": "SP", "s2": "RJ", "s3": "PR"}
PRODUCTS = {"p1": "beleza_saude", "p2": "cama_mesa_banho", "p3": "esporte_lazer"}


def build(drop_state: str | None = "MG", duplicate_payments: bool = False, seed: int = 7) -> duckdb.DuckDBPyConnection:
    rng = random.Random(seed)
    customers = [{"customer_id": f"c{i}", "customer_unique_id": f"u{i}", "customer_zip_code_prefix": 1000 + i,
                  "customer_city": "city", "customer_state": STATES[i % len(STATES)]} for i in range(400)]
    orders, items, payments, reviews = [], [], [], []
    for month_start in (datetime(2018, 3, 1), datetime(2018, 4, 1)):
        in_b = month_start.month == 4
        for c in customers:
            if in_b and c["customer_state"] == drop_state and rng.random() < 0.6:
                continue  # planted cause: most orders from this state disappear in April
            oid = f"o{len(orders)}"
            bought = month_start + timedelta(days=rng.randint(0, 27), hours=rng.randint(0, 23))
            orders.append({"order_id": oid, "customer_id": c["customer_id"], "order_status": "delivered",
                           "order_purchase_timestamp": bought, "order_approved_at": bought,
                           "order_delivered_carrier_date": bought + timedelta(days=1),
                           "order_delivered_customer_date": bought + timedelta(days=rng.randint(3, 12)),
                           "order_estimated_delivery_date": bought + timedelta(days=10)})
            product = rng.choice(list(PRODUCTS))
            items.append({"order_id": oid, "order_item_id": 1, "product_id": product, "seller_id": rng.choice(list(SELLERS)),
                          "shipping_limit_date": bought, "price": 100.0, "freight_value": 10.0})
            payments.append({"order_id": oid, "payment_sequential": 1, "payment_type": rng.choice(["credit_card", "boleto"]),
                             "payment_installments": 1, "payment_value": 110.0})
            if duplicate_payments and in_b:
                payments.append(dict(payments[-1]))  # planted data bug: payment rows duplicated in April
            reviews.append({"review_id": f"r{oid}", "order_id": oid, "review_score": rng.randint(3, 5),
                            "review_creation_date": bought, "review_answer_timestamp": bought})
    frames = {
        "customers": pd.DataFrame(customers),
        "orders": pd.DataFrame(orders),
        "order_items": pd.DataFrame(items),
        "order_payments": pd.DataFrame(payments),
        "order_reviews": pd.DataFrame(reviews),
        "products": pd.DataFrame([{"product_id": k, "product_category_name": v} for k, v in PRODUCTS.items()]),
        "sellers": pd.DataFrame([{"seller_id": k, "seller_zip_code_prefix": 1, "seller_city": "x", "seller_state": v} for k, v in SELLERS.items()]),
    }
    con = duckdb.connect()
    con.execute("CREATE SCHEMA olist")
    for name, df in frames.items():
        con.register("tmp", df)
        con.execute(f"CREATE TABLE olist.{name} AS SELECT * FROM tmp")
        con.unregister("tmp")
    return con


def runner_for(con: duckdb.DuckDBPyConnection):
    def run_sql(sql: str) -> QueryResult:
        return QueryResult(df=con.execute(sql).df(), duration_ms=0)

    return run_sql


def context(_dataset: str) -> str:
    return "Test schema olist (orders, customers, order_items, order_payments, order_reviews, products, sellers)."
