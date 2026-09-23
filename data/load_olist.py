"""Load the 9 Olist CSV files from data/raw/ into PostgreSQL (schema: olist).

Run from the project root:
    python -m data.load_olist
"""

from pathlib import Path

import pandas as pd
from sqlalchemy import text

from backend.config import DATA_SCHEMA, admin_engine

RAW_DIR = Path(__file__).parent / "raw"

# CSV file name -> (table name, columns that hold dates/times)
TABLES = {
    "olist_customers_dataset.csv": ("customers", []),
    "olist_geolocation_dataset.csv": ("geolocation", []),
    "olist_orders_dataset.csv": (
        "orders",
        [
            "order_purchase_timestamp",
            "order_approved_at",
            "order_delivered_carrier_date",
            "order_delivered_customer_date",
            "order_estimated_delivery_date",
        ],
    ),
    "olist_order_items_dataset.csv": ("order_items", ["shipping_limit_date"]),
    "olist_order_payments_dataset.csv": ("order_payments", []),
    "olist_order_reviews_dataset.csv": (
        "order_reviews",
        ["review_creation_date", "review_answer_timestamp"],
    ),
    "olist_products_dataset.csv": ("products", []),
    "olist_sellers_dataset.csv": ("sellers", []),
    "product_category_name_translation.csv": ("category_translation", []),
}

# Primary keys make each row uniquely identifiable and speed up lookups.
# (order_reviews and geolocation contain duplicate ids in the raw data, so they get indexes instead.)
PRIMARY_KEYS = {
    "customers": "customer_id",
    "orders": "order_id",
    "order_items": "order_id, order_item_id",
    "order_payments": "order_id, payment_sequential",
    "products": "product_id",
    "sellers": "seller_id",
    "category_translation": "product_category_name",
}

# Indexes on columns the agent will filter and join on most often.
INDEXES = [
    ("orders", "customer_id"),
    ("orders", "order_purchase_timestamp"),
    ("orders", "order_status"),
    ("order_items", "product_id"),
    ("order_items", "seller_id"),
    ("order_reviews", "order_id"),
    ("geolocation", "geolocation_zip_code_prefix"),
]


def check_files() -> None:
    missing = [name for name in TABLES if not (RAW_DIR / name).exists()]
    if missing:
        raise SystemExit(
            f"Missing files in {RAW_DIR}:\n  " + "\n  ".join(missing)
            + "\nDownload the Olist dataset from Kaggle and extract it into data/raw/."
        )


def load() -> None:
    check_files()
    engine = admin_engine()

    with engine.begin() as conn:
        conn.execute(text(f"CREATE SCHEMA IF NOT EXISTS {DATA_SCHEMA}"))

    for file_name, (table, date_columns) in TABLES.items():
        df = pd.read_csv(RAW_DIR / file_name, parse_dates=date_columns)
        # PostgreSQL allows ~65k values per INSERT, so size each batch by column count.
        chunk_size = max(1, 60_000 // len(df.columns))
        df.to_sql(
            table,
            engine,
            schema=DATA_SCHEMA,
            if_exists="replace",
            index=False,
            chunksize=chunk_size,
            method="multi",
        )
        print(f"Loaded {table:<22} {len(df):>9,} rows")

    with engine.begin() as conn:
        for table, columns in PRIMARY_KEYS.items():
            conn.execute(text(f"ALTER TABLE {DATA_SCHEMA}.{table} ADD PRIMARY KEY ({columns})"))
        for table, column in INDEXES:
            conn.execute(
                text(f"CREATE INDEX IF NOT EXISTS idx_{table}_{column} ON {DATA_SCHEMA}.{table} ({column})")
            )
    print("Primary keys and indexes created.")


if __name__ == "__main__":
    load()
