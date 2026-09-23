import pytest

from backend.guardrails.sql_validator import SQLValidationError, validate_sql


def test_simple_select_gets_schema_and_limit():
    sql = validate_sql("SELECT order_id FROM orders")
    assert "olist.orders" in sql
    assert "LIMIT 1000" in sql


def test_existing_small_limit_is_kept():
    assert "LIMIT 10" in validate_sql("SELECT * FROM orders LIMIT 10")


def test_large_limit_is_capped():
    sql = validate_sql("SELECT * FROM orders LIMIT 999999")
    assert "LIMIT 1000" in sql and "999999" not in sql


def test_cte_names_are_not_schema_qualified():
    sql = validate_sql(
        "WITH monthly AS (SELECT date_trunc('month', order_purchase_timestamp) AS m, COUNT(*) AS n "
        "FROM orders GROUP BY 1) SELECT * FROM monthly"
    )
    assert "olist.orders" in sql
    assert "olist.monthly" not in sql


def test_join_and_window_function_allowed():
    sql = validate_sql(
        "SELECT c.customer_state, COUNT(*) AS n, RANK() OVER (ORDER BY COUNT(*) DESC) AS rnk "
        "FROM orders o JOIN customers c ON o.customer_id = c.customer_id GROUP BY c.customer_state"
    )
    assert "olist.customers" in sql


@pytest.mark.parametrize(
    "bad_sql",
    [
        "DELETE FROM orders",
        "UPDATE orders SET order_status = 'x'",
        "INSERT INTO orders (order_id) VALUES ('x')",
        "DROP TABLE orders",
        "TRUNCATE orders",
        "CREATE TABLE t (id int)",
        "ALTER TABLE orders ADD COLUMN x int",
        "GRANT ALL ON orders TO public",
        "SELECT 1; DROP TABLE orders",
        "SELECT pg_sleep(100)",
        "SELECT pg_read_file('/etc/passwd')",
        "SELECT * INTO copy_of_orders FROM orders",
        "SELECT * FROM orders FOR UPDATE",
        "SELECT * FROM pg_catalog.pg_user",
        "SELECT * FROM public.secrets",
        "WITH d AS (DELETE FROM orders RETURNING *) SELECT * FROM d",
        "this is not sql at all (",
    ],
)
def test_unsafe_queries_are_rejected(bad_sql):
    with pytest.raises(SQLValidationError):
        validate_sql(bad_sql)
