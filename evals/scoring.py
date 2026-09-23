"""Scoring rules for the benchmark. Pure functions, unit-tested."""

import math
from datetime import date, datetime

import pandas as pd


def _cell(value) -> object:
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return None
    if isinstance(value, (pd.Timestamp, datetime, date)):
        return pd.Timestamp(value).date().isoformat()
    if hasattr(value, "item"):  # numpy / Decimal-like scalars
        value = value.item() if not isinstance(value, str) else value
    try:
        return float(value)
    except (TypeError, ValueError):
        return str(value).strip()


def _cells_match(gold, got) -> bool:
    if isinstance(gold, float) and isinstance(got, float):
        return math.isclose(gold, got, rel_tol=1e-3, abs_tol=1e-3)
    return gold == got


def _row_contains(agent_row: list, gold_row: list) -> bool:
    """Every gold cell must appear in the agent row (the agent may add extra columns)."""
    remaining = list(agent_row)
    for g in gold_row:
        for i, a in enumerate(remaining):
            if _cells_match(g, a):
                remaining.pop(i)
                break
        else:
            return False
    return True


def results_match(gold: pd.DataFrame, got: pd.DataFrame) -> bool:
    """Execution accuracy: same number of rows, and each gold row matches a distinct agent row."""
    if len(gold) != len(got):
        return False
    gold_rows = [[_cell(v) for v in row] for row in gold.itertuples(index=False)]
    got_rows = [[_cell(v) for v in row] for row in got.itertuples(index=False)]
    for g in gold_rows:
        for i, a in enumerate(got_rows):
            if _row_contains(a, g):
                got_rows.pop(i)
                break
        else:
            return False
    return True


def hit_rank(candidates: list[dict], expected: tuple[str, str]) -> int | None:
    """1-based rank of the expected (dimension, segment) among the agent's candidates, or None."""
    for rank, c in enumerate(candidates, start=1):
        if c["dimension"] == expected[0] and str(c["segment"]).lower() == str(expected[1]).lower():
            return rank
    return None
