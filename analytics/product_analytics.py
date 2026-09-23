"""Product analytics on Olist: funnel, cohort retention, growth accounting, unit economics.

Every function is plain SQL on the read-only connection, so the same queries can be pasted into
BigQuery / Metabase. Run all and export to Excel:  python -m analytics.product_analytics
"""

from pathlib import Path

import pandas as pd
from sqlalchemy import text

from backend.config import readonly_engine

S = "olist"
OUTPUT = Path(__file__).parent / "output"

FUNNEL = f"""
SELECT COUNT(*)                                                         AS purchased,
       COUNT(order_approved_at)                                         AS approved,
       COUNT(order_delivered_carrier_date)                              AS shipped,
       COUNT(order_delivered_customer_date)                             AS delivered,
       COUNT(*) FILTER (WHERE order_delivered_customer_date IS NOT NULL
                          AND EXISTS (SELECT 1 FROM {S}.order_reviews r
                                      WHERE r.order_id = o.order_id))   AS delivered_and_reviewed
FROM {S}.orders o
"""

# Month-N retention of customers (people = customer_unique_id) by first-purchase month.
COHORTS = f"""
WITH purchases AS (
    SELECT c.customer_unique_id AS person, date_trunc('month', o.order_purchase_timestamp)::date AS month
    FROM {S}.orders o JOIN {S}.customers c USING (customer_id)
    WHERE o.order_status NOT IN ('canceled', 'unavailable')
    GROUP BY 1, 2
), first AS (
    SELECT person, MIN(month) AS cohort FROM purchases GROUP BY person
)
SELECT f.cohort,
       (EXTRACT(YEAR FROM p.month) - EXTRACT(YEAR FROM f.cohort)) * 12
         + EXTRACT(MONTH FROM p.month) - EXTRACT(MONTH FROM f.cohort) AS months_since_first,
       COUNT(DISTINCT p.person) AS customers
FROM purchases p JOIN first f USING (person)
WHERE f.cohort >= '2017-01-01' AND f.cohort < '2018-09-01'
GROUP BY 1, 2
ORDER BY 1, 2
"""

# Each month's active customers split into new / retained (active last month) / resurrected; plus churned.
GROWTH_ACCOUNTING = f"""
WITH active AS (
    SELECT DISTINCT c.customer_unique_id AS person, date_trunc('month', o.order_purchase_timestamp)::date AS month
    FROM {S}.orders o JOIN {S}.customers c USING (customer_id)
    WHERE o.order_status NOT IN ('canceled', 'unavailable')
), flags AS (
    SELECT a.month, a.person,
           MIN(a.month) OVER (PARTITION BY a.person) AS first_month,
           LAG(a.month) OVER (PARTITION BY a.person ORDER BY a.month) AS prev_month
    FROM active a
), classified AS (
    SELECT month,
           CASE WHEN month = first_month THEN 'new'
                WHEN prev_month = (month - interval '1 month')::date THEN 'retained'
                ELSE 'resurrected' END AS kind
    FROM flags
), churned AS (
    SELECT (a.month + interval '1 month')::date AS month, COUNT(*) AS churned
    FROM active a LEFT JOIN active b ON b.person = a.person AND b.month = (a.month + interval '1 month')::date
    WHERE b.person IS NULL GROUP BY 1
)
SELECT c.month,
       COUNT(*) FILTER (WHERE kind = 'new')         AS new,
       COUNT(*) FILTER (WHERE kind = 'retained')    AS retained,
       COUNT(*) FILTER (WHERE kind = 'resurrected') AS resurrected,
       COALESCE(MAX(ch.churned), 0)                 AS churned
FROM classified c LEFT JOIN churned ch USING (month)
WHERE c.month >= '2017-01-01' AND c.month < '2018-09-01'
GROUP BY c.month ORDER BY c.month
"""

UNIT_ECONOMICS = f"""
WITH orders AS (
    SELECT o.order_id, date_trunc('month', o.order_purchase_timestamp)::date AS month,
           SUM(oi.price) AS items, SUM(oi.freight_value) AS freight
    FROM {S}.orders o JOIN {S}.order_items oi USING (order_id)
    WHERE o.order_status NOT IN ('canceled', 'unavailable')
    GROUP BY 1, 2
)
SELECT month, COUNT(*) AS orders, ROUND(SUM(items)::numeric, 2) AS item_revenue,
       ROUND(AVG(items + freight)::numeric, 2) AS avg_order_value,
       ROUND((SUM(freight) / NULLIF(SUM(items + freight), 0))::numeric, 4) AS freight_share
FROM orders WHERE month >= '2017-01-01' AND month < '2018-09-01'
GROUP BY month ORDER BY month
"""


def run(sql: str) -> pd.DataFrame:
    with readonly_engine().connect() as conn:
        return pd.read_sql(text(sql), conn)


def funnel() -> pd.DataFrame:
    row = run(FUNNEL).iloc[0]
    df = pd.DataFrame({"step": row.index, "orders": row.values.astype(int)})
    df["conversion_from_start"] = df["orders"] / df["orders"].iloc[0]
    df["conversion_from_previous"] = df["orders"] / df["orders"].shift(1).fillna(df["orders"].iloc[0])
    return df


def cohort_retention() -> pd.DataFrame:
    df = run(COHORTS)
    matrix = df.pivot(index="cohort", columns="months_since_first", values="customers").fillna(0)
    return matrix.div(matrix[0], axis=0).round(4)


def growth_accounting() -> pd.DataFrame:
    df = run(GROWTH_ACCOUNTING)
    df["quick_ratio"] = ((df["new"] + df["resurrected"]) / df["churned"].where(df["churned"] > 0)).round(3)
    return df


def unit_economics() -> pd.DataFrame:
    return run(UNIT_ECONOMICS)


def export() -> Path:
    OUTPUT.mkdir(exist_ok=True)
    path = OUTPUT / "olist_product_analytics.xlsx"
    with pd.ExcelWriter(path, engine="openpyxl") as xl:
        funnel().to_excel(xl, sheet_name="funnel", index=False)
        cohort_retention().to_excel(xl, sheet_name="cohort_retention")
        growth_accounting().to_excel(xl, sheet_name="growth_accounting", index=False)
        unit_economics().to_excel(xl, sheet_name="unit_economics", index=False)
    return path


if __name__ == "__main__":
    print(f"Wrote {export()}")
