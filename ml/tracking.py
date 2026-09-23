"""Experiment tracking with MLflow (local SQLite store ml/mlflow.db). View with:  mlflow ui --backend-store-uri sqlite:///ml/mlflow.db"""

import json
from pathlib import Path

import mlflow

ML_DIR = Path(__file__).parent
REPORTS = ML_DIR / "reports"


def start(experiment: str):
    mlflow.set_tracking_uri(f"sqlite:///{(ML_DIR / 'mlflow.db').resolve().as_posix()}")
    mlflow.set_experiment(experiment)
    return mlflow.start_run()


def save_report(name: str, report: dict) -> Path:
    REPORTS.mkdir(exist_ok=True)
    path = REPORTS / f"{name}.json"
    path.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
    return path
