"""Remaining useful life (RUL) of turbofan engines, on NASA CMAPSS FD001 (real benchmark data).

Train: 100 engines recorded every cycle until failure. Test: 100 engines cut off before failure,
with the true remaining cycles given. We predict RUL at each test engine's last recorded cycle.

Standard practice: cap the training target at 125 cycles ("piecewise-linear RUL"), because a
brand-new engine and one at mid-life look the same to the sensors.
Metrics: RMSE, and NASA's asymmetric score that punishes LATE predictions (predicting more life than is left) harder.

    python -m iot.rul      (needs data/raw/cmapss from NASA; see README)
"""

from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.linear_model import Ridge

from ml import tracking

DATA = Path(__file__).resolve().parents[1] / "data" / "raw" / "cmapss"
COLS = ["unit", "cycle", "op1", "op2", "op3"] + [f"s{i}" for i in range(1, 22)]
RUL_CAP = 125
WINDOW = 30


def read(name: str) -> pd.DataFrame:
    return pd.read_csv(DATA / name, sep=r"\s+", header=None, names=COLS)


def informative_sensors(train: pd.DataFrame) -> list[str]:
    """Drop sensors that never change in FD001 (single operating condition)."""
    return [c for c in COLS[5:] if train[c].std() > 1e-4]


def window_features(df: pd.DataFrame, sensors: list[str]) -> pd.DataFrame:
    """Per cycle: current value, rolling mean, and rolling slope of each sensor over the last WINDOW cycles."""
    out = df[["unit", "cycle"]].copy()
    g = df.groupby("unit")
    for s in sensors:
        out[s] = df[s]
        out[f"{s}_mean"] = g[s].transform(lambda x: x.rolling(WINDOW, min_periods=1).mean())
        out[f"{s}_slope"] = g[s].transform(lambda x: x.diff().rolling(WINDOW, min_periods=2).mean())
    return out.fillna(0.0)


def add_train_target(train: pd.DataFrame) -> pd.Series:
    max_cycle = train.groupby("unit")["cycle"].transform("max")
    return (max_cycle - train["cycle"]).clip(upper=RUL_CAP)


def nasa_score(true: np.ndarray, pred: np.ndarray) -> float:
    d = pred - true
    return float(np.sum(np.where(d < 0, np.exp(-d / 13) - 1, np.exp(d / 10) - 1)))


def evaluate() -> dict:
    train, test = read("train_FD001.txt"), read("test_FD001.txt")
    true_rul = pd.read_csv(DATA / "RUL_FD001.txt", header=None)[0].to_numpy()
    sensors = informative_sensors(train)
    X_train = window_features(train, sensors)
    y_train = add_train_target(train)
    X_test_all = window_features(test, sensors)
    X_test = X_test_all.groupby("unit").tail(1).sort_values("unit")  # last observed cycle of each test engine
    features = [c for c in X_train.columns if c not in ("unit", "cycle")]

    predictions = {
        "mean_baseline": np.full(len(X_test), y_train.mean()),
        "ridge": Ridge(alpha=1.0).fit(X_train[features], y_train).predict(X_test[features]),
        "gradient_boosting": HistGradientBoostingRegressor(max_iter=400, learning_rate=0.05, random_state=0)
        .fit(X_train[features], y_train).predict(X_test[features]),
    }
    capped_true = np.minimum(true_rul, RUL_CAP)
    results = {name: {"rmse": round(float(np.sqrt(np.mean((np.clip(p, 0, RUL_CAP) - capped_true) ** 2))), 2),
                      "nasa_score": round(nasa_score(capped_true, np.clip(p, 0, RUL_CAP)), 1)}
               for name, p in predictions.items()}
    return {"dataset": "CMAPSS FD001", "train_engines": int(train["unit"].nunique()), "test_engines": int(len(X_test)),
            "sensors_used": sensors, "rul_cap": RUL_CAP, "window": WINDOW, "models": results}


def main() -> None:
    report = evaluate()
    with tracking.start("turbofan_rul"):
        import mlflow

        for name, m in report["models"].items():
            mlflow.log_metric(f"{name}_rmse", m["rmse"])
            mlflow.log_metric(f"{name}_nasa_score", m["nasa_score"])
    print(tracking.save_report("turbofan_rul", report))
    for name, m in report["models"].items():
        print(f"{name:<18} RMSE {m['rmse']:>6}   NASA score {m['nasa_score']:>9}")


if __name__ == "__main__":
    main()
