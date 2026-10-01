"""The SQL guardrail on the MySQL dialect: same rules as PostgreSQL, plus MySQL's own dangerous functions."""
import pytest

from backend.guardrails.sql_validator import SQLValidationError, validate_sql

M = {"dialect": "mysql", "allowed_schemas": frozenset({"olist"}), "default_schema": "olist"}


def test_read_query_gets_schema_and_limit_in_mysql_syntax():
    out = validate_sql("SELECT customer_state, COUNT(*) AS n FROM orders GROUP BY customer_state", **M)
    assert "olist.orders" in out and out.rstrip().endswith("LIMIT 1000")


def test_backtick_identifiers_parse():
    out = validate_sql("SELECT `order_id` FROM `orders` WHERE `order_status` = 'delivered' LIMIT 5", **M)
    assert "LIMIT 5" in out


@pytest.mark.parametrize("sql", [
    "SELECT SLEEP(10)",
    "SELECT BENCHMARK(1000000, MD5('x'))",
    "SELECT LOAD_FILE('/etc/passwd')",
    "SELECT GET_LOCK('k', 10)",
])
def test_mysql_dangerous_functions_are_blocked(sql):
    with pytest.raises(SQLValidationError, match="Forbidden function"):
        validate_sql(sql, **M)


@pytest.mark.parametrize("sql", [
    "SELECT order_id FROM orders INTO OUTFILE '/tmp/x.csv'",
    "DELETE FROM orders",
    "SELECT 1; DROP TABLE orders",
    "SELECT * FROM mysql.user",
    "SELECT * FROM orders FOR UPDATE",
])
def test_writes_files_other_schemas_and_locks_are_blocked(sql):
    with pytest.raises(SQLValidationError):
        validate_sql(sql, **M)


def test_unknown_dialect_rejected_and_postgres_default_unchanged():
    with pytest.raises(SQLValidationError, match="Unsupported"):
        validate_sql("SELECT 1", dialect="oracle")
    assert "LIMIT 1000" in validate_sql("SELECT order_id FROM orders")
