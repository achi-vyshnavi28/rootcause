"""Validated SQL actually runs on MySQL. Needs a server: set ROOTCAUSE_MYSQL_URL (CI starts a mysql:8 service)."""
import os

import pytest

from backend.guardrails.sql_validator import SQLValidationError, validate_sql

URL = os.getenv("ROOTCAUSE_MYSQL_URL")
pytestmark = pytest.mark.skipif(not URL, reason="ROOTCAUSE_MYSQL_URL not set")
M = {"dialect": "mysql", "allowed_schemas": frozenset({"olist"}), "default_schema": "olist"}


@pytest.fixture(scope="module")
def engine():
    from sqlalchemy import create_engine, text

    eng = create_engine(URL)
    with eng.begin() as c:
        c.execute(text("CREATE DATABASE IF NOT EXISTS olist"))
        c.execute(text("DROP TABLE IF EXISTS olist.orders"))
        c.execute(text("CREATE TABLE olist.orders (order_id VARCHAR(32) PRIMARY KEY, customer_state CHAR(2),"
                       " order_status VARCHAR(16), purchased_at DATETIME)"))
        c.execute(text("INSERT INTO olist.orders VALUES ('a','SP','delivered','2018-03-02'),"
                       " ('b','SP','delivered','2018-04-03'), ('c','MG','delivered','2018-03-05'),"
                       " ('d','MG','canceled','2018-03-09'), ('e','RJ','delivered','2018-04-11')"))
    yield eng
    eng.dispose()


def run(engine, sql):
    from sqlalchemy import text

    with engine.connect() as c:
        return c.execute(text(validate_sql(sql, **M))).fetchall()


def test_period_comparison_by_segment_runs_on_mysql(engine):
    rows = run(engine, """
        SELECT customer_state,
               SUM(CASE WHEN purchased_at < '2018-04-01' THEN 1 ELSE 0 END) AS march,
               SUM(CASE WHEN purchased_at >= '2018-04-01' THEN 1 ELSE 0 END) AS april
        FROM orders GROUP BY customer_state ORDER BY customer_state""")
    assert [tuple(r) for r in rows] == [("MG", 2, 0), ("RJ", 0, 1), ("SP", 1, 1)]


def test_window_function_runs_on_mysql(engine):
    rows = run(engine, "SELECT order_id, ROW_NUMBER() OVER (PARTITION BY customer_state ORDER BY purchased_at) AS rn"
                       " FROM orders ORDER BY order_id")
    assert [r.rn for r in rows] == [1, 2, 1, 2, 1]


def test_blocked_query_never_reaches_mysql(engine):
    with pytest.raises(SQLValidationError):
        run(engine, "SELECT SLEEP(5)")
