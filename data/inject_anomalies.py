"""Create schema olist_lab: a copy of Olist with 5 planted problems whose root cause we KNOW.

The evals ask RootCause "why did X change?" on this copy and check whether it finds the planted cause.
Each scenario uses its own months so they don't interfere. Selection is deterministic (md5 of ids).

Run from the project root (after load_olist and setup_readonly_role):
    python -m data.inject_anomalies
"""

import os

from sqlalchemy import text

from backend.config import DATA_SCHEMA, LAB_SCHEMA, admin_engine

TABLES = ["customers", "orders", "order_items", "order_payments", "order_reviews", "products", "sellers", "category_translation"]
PRIMARY_KEYS = {  # order_payments gets no key: scenario 5 duplicates its rows on purpose
    "customers": "customer_id", "orders": "order_id", "order_items": "order_id, order_item_id",
    "products": "product_id", "sellers": "seller_id", "category_translation": "product_category_name",
}
L = LAB_SCHEMA


def pick(column: str, percent: int) -> str:
    """Deterministically select ~percent% of rows."""
    return f"(('x' || substr(md5({column}), 1, 8))::bit(32)::int & 2147483647) % 100 < {percent}"


SCENARIOS = {
    "S1_orders_drop_mg": {
        "description": "April 2018: 60% of orders from customers in MG removed (orders drop vs March).",
        "sql": [
            f"""CREATE TEMP TABLE s1 AS SELECT o.order_id FROM {L}.orders o JOIN {L}.customers c USING (customer_id)
                WHERE c.customer_state = 'MG' AND o.order_purchase_timestamp >= '2018-04-01'
                AND o.order_purchase_timestamp < '2018-05-01' AND {pick('o.order_id', 60)}""",
            *[f"DELETE FROM {L}.{t} WHERE order_id IN (SELECT order_id FROM s1)"
              for t in ("order_items", "order_payments", "order_reviews", "orders")],
        ],
    },
    "S2_late_spike_sp": {
        "description": "June 2018: 40% of delivered orders to SP customers arrive 7 days after the promised date.",
        "sql": [
            f"""UPDATE {L}.orders o SET order_delivered_customer_date = o.order_estimated_delivery_date + INTERVAL '7 days'
                FROM {L}.customers c WHERE c.customer_id = o.customer_id AND c.customer_state = 'SP'
                AND o.order_status = 'delivered' AND o.order_purchase_timestamp >= '2018-06-01'
                AND o.order_purchase_timestamp < '2018-07-01' AND {pick('o.order_id', 40)}""",
        ],
    },
    "S3_boleto_cancellations": {
        "description": "August 2018: 50% of orders paid by boleto are canceled (cancellation rate up vs July).",
        "sql": [
            f"""UPDATE {L}.orders o SET order_status = 'canceled'
                WHERE o.order_purchase_timestamp >= '2018-08-01' AND o.order_purchase_timestamp < '2018-09-01'
                AND o.order_id IN (SELECT order_id FROM {L}.order_payments WHERE payment_type = 'boleto')
                AND {pick('o.order_id', 50)}""",
        ],
    },
    "S4_health_beauty_reviews": {
        "description": "May 2018: 70% of reviews on orders containing beleza_saude products become 1-star.",
        "sql": [
            f"""UPDATE {L}.order_reviews r SET review_score = 1
                WHERE r.order_id IN (
                    SELECT o.order_id FROM {L}.orders o JOIN {L}.order_items oi USING (order_id)
                    JOIN {L}.products p USING (product_id)
                    WHERE p.product_category_name = 'beleza_saude'
                    AND o.order_purchase_timestamp >= '2018-05-01' AND o.order_purchase_timestamp < '2018-06-01')
                AND {pick('r.review_id', 70)}""",
        ],
    },
    "S5_duplicate_payments": {
        "description": "October 2017: payment rows of 40% of orders are duplicated by a (simulated) ETL bug.",
        "sql": [
            f"""INSERT INTO {L}.order_payments
                SELECT op.* FROM {L}.order_payments op JOIN {L}.orders o USING (order_id)
                WHERE o.order_purchase_timestamp >= '2017-10-01' AND o.order_purchase_timestamp < '2017-11-01'
                AND {pick('o.order_id', 40)}""",
        ],
    },
}


def build() -> None:
    reader = os.environ["READONLY_DB_USER"]
    with admin_engine().begin() as conn:
        conn.execute(text(f"DROP SCHEMA IF EXISTS {L} CASCADE"))
        conn.execute(text(f"CREATE SCHEMA {L}"))
        for t in TABLES:
            conn.execute(text(f"CREATE TABLE {L}.{t} AS SELECT * FROM {DATA_SCHEMA}.{t}"))
        for t, cols in PRIMARY_KEYS.items():
            conn.execute(text(f"ALTER TABLE {L}.{t} ADD PRIMARY KEY ({cols})"))
        for name, scenario in SCENARIOS.items():
            for statement in scenario["sql"]:
                conn.execute(text(statement))
            conn.execute(text("DROP TABLE IF EXISTS s1"))
            print(f"Planted {name}: {scenario['description']}")
        conn.execute(text(f"CREATE INDEX ON {L}.orders (order_purchase_timestamp)"))
        conn.execute(text(f"CREATE INDEX ON {L}.order_payments (order_id)"))
        conn.execute(text(f"CREATE INDEX ON {L}.order_reviews (order_id)"))
        conn.execute(text(f'GRANT USAGE ON SCHEMA {L} TO "{reader}"'))
        conn.execute(text(f'GRANT SELECT ON ALL TABLES IN SCHEMA {L} TO "{reader}"'))
    print(f"Schema {L} ready; read access granted to {reader}.")


if __name__ == "__main__":
    build()
