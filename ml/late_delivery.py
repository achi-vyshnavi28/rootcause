"""Predict, at purchase time, whether an order will arrive after the promised date.

Only features known when the order is placed are used (no leakage from delivery data).
Split by time: train on older orders, test on the most recent ones, like production.

    python -m ml.late_delivery
"""

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, roc_auc_score
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import OneHotEncoder, OrdinalEncoder, StandardScaler
from sqlalchemy import text

from backend.config import readonly_engine
from ml import tracking

SQL = """
SELECT o.order_purchase_timestamp AS purchased_at,
       (o.order_delivered_customer_date > o.order_estimated_delivery_date)::int AS late,
       EXTRACT(EPOCH FROM (o.order_estimated_delivery_date - o.order_purchase_timestamp)) / 86400 AS promised_days,
       c.customer_state, s.seller_state, (c.customer_state = s.seller_state)::int AS same_state,
       SUM(oi.price) AS order_value, SUM(oi.freight_value) AS freight, COUNT(*) AS n_items,
       COUNT(DISTINCT oi.seller_id) AS n_sellers, MAX(p.product_weight_g) AS max_weight_g,
       MAX(COALESCE(p.product_category_name, 'unknown')) AS category
FROM olist.orders o
JOIN olist.customers c USING (customer_id)
JOIN olist.order_items oi USING (order_id)
JOIN olist.sellers s ON s.seller_id = oi.seller_id
JOIN olist.products p ON p.product_id = oi.product_id
WHERE o.order_status = 'delivered' AND o.order_delivered_customer_date IS NOT NULL
GROUP BY o.order_id, o.order_purchase_timestamp, o.order_delivered_customer_date, o.order_estimated_delivery_date,
         c.customer_state, s.seller_state
"""

NUMERIC = ["promised_days", "same_state", "order_value", "freight", "n_items", "n_sellers", "max_weight_g", "month", "weekday"]
CATEGORICAL = ["customer_state", "seller_state", "category"]


def load() -> pd.DataFrame:
    with readonly_engine().connect() as conn:
        df = pd.read_sql(text(SQL), conn)
    df = df.sort_values("purchased_at").drop_duplicates()
    df["month"], df["weekday"] = df["purchased_at"].dt.month, df["purchased_at"].dt.dayofweek
    df["freight_ratio"] = df["freight"] / df["order_value"].replace(0, np.nan)
    df["max_weight_g"] = df["max_weight_g"].fillna(df["max_weight_g"].median())
    return df


def models() -> dict:
    baseline = make_pipeline(
        ColumnTransformer([("num", StandardScaler(), NUMERIC), ("cat", OneHotEncoder(handle_unknown="ignore", min_frequency=50), CATEGORICAL)]),
        LogisticRegression(max_iter=2000, class_weight="balanced"),
    )
    boosted = make_pipeline(
        ColumnTransformer([("num", "passthrough", NUMERIC),
                           ("cat", OrdinalEncoder(handle_unknown="use_encoded_value", unknown_value=-1), CATEGORICAL)]),
        HistGradientBoostingClassifier(max_iter=300, learning_rate=0.05, categorical_features=list(range(len(NUMERIC), len(NUMERIC) + len(CATEGORICAL))),
                                       class_weight="balanced", random_state=0),
    )
    return {"logistic_regression": baseline, "gradient_boosting": boosted}


def main() -> None:
    df = load()
    cut = df["purchased_at"].quantile(0.8)  # last 20% of time = test set
    train, test = df[df["purchased_at"] < cut], df[df["purchased_at"] >= cut]
    results = {}
    with tracking.start("late_delivery"):
        import mlflow

        mlflow.log_params({"train_rows": len(train), "test_rows": len(test), "split": f"time < {cut:%Y-%m-%d}"})
        for name, model in models().items():
            model.fit(train[NUMERIC + CATEGORICAL], train["late"])
            proba = model.predict_proba(test[NUMERIC + CATEGORICAL])[:, 1]
            top_decile = test.assign(p=proba).nlargest(len(test) // 10, "p")["late"].mean()
            results[name] = {"roc_auc": round(roc_auc_score(test["late"], proba), 4),
                             "pr_auc": round(average_precision_score(test["late"], proba), 4),
                             "late_rate_in_top_10pct_risk": round(float(top_decile), 4)}
            for metric, value in results[name].items():
                mlflow.log_metric(f"{name}_{metric}", value)
    report = {"task": "predict late delivery at purchase time", "test_late_rate": round(float(test["late"].mean()), 4),
              "train_rows": len(train), "test_rows": len(test), "models": results}
    print(tracking.save_report("late_delivery", report))
    print(report)


if __name__ == "__main__":
    main()
