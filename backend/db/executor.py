"""Runs validated SQL on the read-only connection and returns a DataFrame."""

import time
from dataclasses import dataclass

import pandas as pd
from sqlalchemy import text

from backend.config import readonly_engine


@dataclass
class QueryResult:
    df: pd.DataFrame
    duration_ms: int


def run_readonly_sql(sql: str) -> QueryResult:
    started = time.perf_counter()
    with readonly_engine().connect() as conn:
        df = pd.read_sql(text(sql), conn)
    return QueryResult(df=df, duration_ms=int((time.perf_counter() - started) * 1000))
