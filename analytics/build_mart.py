"""Build schema olist_mart: a star schema for BI tools (Power BI / Looker Studio / Metabase).

    fact_order_items (grain: one row per item sold)  --> dim_date, dim_customer, dim_seller, dim_product
    fact_payments    (grain: one row per payment)    --> dim_date, dim_customer

Run from the project root:  python -m analytics.build_mart
"""

import os

from sqlalchemy import text

from backend.config import admin_engine

M, S = "olist_mart", "olist"

STATEMENTS = [
    f"DROP SCHEMA IF EXISTS {M} CASCADE",
    f"CREATE SCHEMA {M}",
    f"""CREATE TABLE {M}.dim_date AS
        SELECT d::date AS date_key, EXTRACT(YEAR FROM d)::int AS year, EXTRACT(QUARTER FROM d)::int AS quarter,
               EXTRACT(MONTH FROM d)::int AS month, TO_CHAR(d, 'YYYY-MM') AS year_month,
               EXTRACT(ISODOW FROM d)::int AS weekday, EXTRACT(ISODOW FROM d) IN (6, 7) AS is_weekend
        FROM generate_series('2016-01-01'::date, '2018-12-31'::date, interval '1 day') d""",
    f"""CREATE TABLE {M}.dim_customer AS
        SELECT customer_id, customer_unique_id, customer_city, customer_state FROM {S}.customers""",
    f"""CREATE TABLE {M}.dim_seller AS SELECT seller_id, seller_city, seller_state FROM {S}.sellers""",
    f"""CREATE TABLE {M}.dim_product AS
        SELECT p.product_id, COALESCE(p.product_category_name, 'unknown') AS category_pt,
               COALESCE(t.product_category_name_english, 'unknown') AS category_en,
               p.product_weight_g, p.product_photos_qty
        FROM {S}.products p LEFT JOIN {S}.category_translation t USING (product_category_name)""",
    f"""CREATE TABLE {M}.fact_order_items AS
        SELECT oi.order_id, oi.order_item_id, o.customer_id, oi.seller_id, oi.product_id,
               o.order_purchase_timestamp::date AS purchase_date_key, o.order_status,
               oi.price, oi.freight_value, oi.price + oi.freight_value AS item_total,
               CASE WHEN o.order_status = 'delivered' AND o.order_delivered_customer_date IS NOT NULL
                    THEN (o.order_delivered_customer_date > o.order_estimated_delivery_date)::int END AS is_late,
               EXTRACT(EPOCH FROM (o.order_delivered_customer_date - o.order_purchase_timestamp)) / 86400 AS delivery_days,
               r.review_score
        FROM {S}.order_items oi
        JOIN {S}.orders o USING (order_id)
        LEFT JOIN (SELECT order_id, AVG(review_score) AS review_score FROM {S}.order_reviews GROUP BY order_id) r USING (order_id)""",
    f"""CREATE TABLE {M}.fact_payments AS
        SELECT op.order_id, op.payment_sequential, o.customer_id, o.order_purchase_timestamp::date AS purchase_date_key,
               op.payment_type, op.payment_installments, op.payment_value
        FROM {S}.order_payments op JOIN {S}.orders o USING (order_id)""",
    f"ALTER TABLE {M}.dim_date ADD PRIMARY KEY (date_key)",
    f"ALTER TABLE {M}.dim_customer ADD PRIMARY KEY (customer_id)",
    f"ALTER TABLE {M}.dim_seller ADD PRIMARY KEY (seller_id)",
    f"ALTER TABLE {M}.dim_product ADD PRIMARY KEY (product_id)",
    f"ALTER TABLE {M}.fact_order_items ADD PRIMARY KEY (order_id, order_item_id)",
    f"ALTER TABLE {M}.fact_payments ADD PRIMARY KEY (order_id, payment_sequential)",
    f"CREATE INDEX ON {M}.fact_order_items (purchase_date_key)",
    f"CREATE INDEX ON {M}.fact_payments (purchase_date_key)",
]


def build() -> None:
    reader = os.environ["READONLY_DB_USER"]
    with admin_engine().begin() as conn:
        for s in STATEMENTS:
            conn.execute(text(s))
        conn.execute(text(f'GRANT USAGE ON SCHEMA {M} TO "{reader}"'))
        conn.execute(text(f'GRANT SELECT ON ALL TABLES IN SCHEMA {M} TO "{reader}"'))
        counts = {t: conn.execute(text(f"SELECT COUNT(*) FROM {M}.{t}")).scalar()
                  for t in ("dim_date", "dim_customer", "dim_seller", "dim_product", "fact_order_items", "fact_payments")}
    for t, n in counts.items():
        print(f"{M}.{t:<18} {n:>9,} rows")


if __name__ == "__main__":
    build()
