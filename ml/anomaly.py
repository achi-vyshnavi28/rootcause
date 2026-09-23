"""Anomaly scanner for daily business metrics: STL decomposition + robust z-score on the residual.

STL removes the trend and the weekly pattern (Mondays are always busier), so what is left is the
unexplained part. A day is anomalous when that residual is far from normal, measured with the
median absolute deviation (MAD), which a few extreme days cannot distort the way a standard deviation can.

    python -m ml.anomaly --dataset olist_lab
"""

import argparse

import numpy as np
import pandas as pd
from sqlalchemy import text
from statsmodels.tsa.seasonal import STL

from backend.config import readonly_engine

METRICS = {
    "orders": "COUNT(*)",
    "canceled_rate": "AVG(CASE WHEN order_status = 'canceled' THEN 1.0 ELSE 0 END)",
    "late_rate": "AVG(CASE WHEN order_status = 'delivered' AND order_delivered_customer_date IS NOT NULL "
                 "THEN (order_delivered_customer_date > order_estimated_delivery_date)::int END)",
}


def daily_series(dataset: str, metric: str, start: str = "2017-03-01", end: str = "2018-08-15") -> pd.Series:
    sql = (f"SELECT order_purchase_timestamp::date AS day, {METRICS[metric]} AS value FROM {dataset}.orders "
           f"WHERE order_purchase_timestamp >= :s AND order_purchase_timestamp < :e GROUP BY 1 ORDER BY 1")
    with readonly_engine().connect() as conn:
        df = pd.read_sql(text(sql), conn, params={"s": start, "e": end})
    s = df.set_index(pd.to_datetime(df["day"]))["value"].astype(float)
    return s.asfreq("D").interpolate()


def detect(series: pd.Series, period: int = 7, threshold: float = 6.0) -> pd.DataFrame:
    fit = STL(series, period=period, robust=True).fit()
    resid = fit.resid
    mad = np.median(np.abs(resid - np.median(resid))) or 1e-9
    z = 0.6745 * (resid - np.median(resid)) / mad  # 0.6745 makes MAD comparable to a std dev
    out = pd.DataFrame({"value": series, "expected": fit.trend + fit.seasonal, "robust_z": z})
    return out[np.abs(out["robust_z"]) >= threshold].sort_values("robust_z", key=abs, ascending=False)


def scan(dataset: str, threshold: float = 6.0) -> list[dict]:
    findings = []
    for metric in METRICS:
        for day, row in detect(daily_series(dataset, metric), threshold=threshold).iterrows():
            findings.append({"metric": metric, "day": day.date().isoformat(), "value": round(float(row["value"]), 4),
                             "expected": round(float(row["expected"]), 4), "robust_z": round(float(row["robust_z"]), 2)})
    return sorted(findings, key=lambda f: abs(f["robust_z"]), reverse=True)


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--dataset", default="olist_lab")
    p.add_argument("--threshold", type=float, default=6.0)
    args = p.parse_args()
    for f in scan(args.dataset, args.threshold)[:20]:
        print(f)
