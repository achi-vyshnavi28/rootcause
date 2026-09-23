"""Forecast daily orders 28 days ahead. Three models compared with rolling-origin backtesting.

- seasonal naive: "same weekday last week" (the baseline every model must beat)
- Holt-Winters: exponential smoothing with trend + weekly seasonality
- gradient boosting: lag and calendar features (HistGradientBoostingRegressor)

    python -m ml.forecast
"""

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingRegressor
from statsmodels.tsa.holtwinters import ExponentialSmoothing

from ml import tracking
from ml.anomaly import daily_series

HORIZON = 28


def mape(actual: np.ndarray, pred: np.ndarray) -> float:
    return float(np.mean(np.abs((actual - pred) / actual)) * 100)


def seasonal_naive(train: pd.Series, horizon: int) -> np.ndarray:
    return np.array([train.iloc[-7 + (i % 7)] for i in range(horizon)])


def holt_winters(train: pd.Series, horizon: int) -> np.ndarray:
    model = ExponentialSmoothing(train, trend="add", damped_trend=True, seasonal="add", seasonal_periods=7).fit()
    return model.forecast(horizon).to_numpy()


def _features(s: pd.Series) -> pd.DataFrame:
    df = pd.DataFrame({"y": s})
    for lag in (7, 14, 21, 28):
        df[f"lag_{lag}"] = s.shift(lag)
    df["rolling_28"] = s.shift(7).rolling(28).mean()
    df["weekday"] = s.index.dayofweek
    df["month"] = s.index.month
    df["day_of_month"] = s.index.day
    return df


def gradient_boosting(train: pd.Series, horizon: int) -> np.ndarray:
    """Recursive multi-step forecast: predict one day, append it, predict the next."""
    history = train.copy()
    model = HistGradientBoostingRegressor(max_iter=300, learning_rate=0.05, random_state=0)
    feats = _features(history).dropna()
    model.fit(feats.drop(columns="y"), feats["y"])
    preds = []
    for _ in range(horizon):
        nxt = history.index[-1] + pd.Timedelta(days=1)
        extended = pd.concat([history, pd.Series([np.nan], index=[nxt])])
        x = _features(extended).drop(columns="y").iloc[[-1]]
        y = float(model.predict(x)[0])
        preds.append(y)
        history = pd.concat([history, pd.Series([y], index=[nxt])])
    return np.array(preds)


MODELS = {"seasonal_naive": seasonal_naive, "holt_winters": holt_winters, "gradient_boosting": gradient_boosting}


def backtest(series: pd.Series, folds: int = 4) -> pd.DataFrame:
    rows = []
    for k in range(folds, 0, -1):
        cut = len(series) - k * HORIZON
        train, test = series.iloc[:cut], series.iloc[cut: cut + HORIZON]
        for name, fn in MODELS.items():
            rows.append({"fold_end": test.index[-1].date(), "model": name, "mape": mape(test.to_numpy(), fn(train, HORIZON))})
    return pd.DataFrame(rows)


def main() -> None:
    series = daily_series("olist", "orders", "2017-03-01", "2018-08-15")
    results = backtest(series)
    summary = results.groupby("model")["mape"].mean().sort_values()
    with tracking.start("orders_forecast"):
        import mlflow

        for name, value in summary.items():
            mlflow.log_metric(f"mape_{name}", value)
        mlflow.log_param("horizon_days", HORIZON)
    report = {"horizon_days": HORIZON, "folds": int(results["fold_end"].nunique()),
              "mean_mape_pct": summary.round(2).to_dict(), "best_model": summary.index[0],
              "per_fold": results.round(2).to_dict(orient="records")}
    print(tracking.save_report("forecast", report))
    print(summary.round(2).to_string())


if __name__ == "__main__":
    main()
