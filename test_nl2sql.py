import sqlite3

import pytest

from assistant import AssistantError, ask
from db import create_database, get_readonly_connection, get_schema_text
from sql_guard import UnsafeSQLError, validate_sql


@pytest.fixture(scope="module")
def conn(tmp_path_factory):
    path = create_database(tmp_path_factory.mktemp("db") / "t.db")
    return get_readonly_connection(path)


class FakeLLM:
    def __init__(self, *outputs):
        self.outputs = list(outputs)
        self.calls = []

    def generate_sql(self, q, schema, prev_sql=None, prev_err=None):
        self.calls.append((prev_sql, prev_err))
        return self.outputs.pop(0)

    def summarize(self, q, sql, cols, rows):
        return f"{len(rows)} rows"


@pytest.mark.parametrize("bad", [
    "DELETE FROM customers", "DROP TABLE orders", "SELECT 1; DROP TABLE orders",
    "UPDATE products SET price = 0", "PRAGMA table_info(orders)", "INSERT INTO orders VALUES (1)",
    "", "   ",
])
def test_guard_rejects(bad):
    with pytest.raises(UnsafeSQLError):
        validate_sql(bad)


def test_guard_accepts_and_cleans():
    assert validate_sql("```sql\nSELECT * FROM customers;\n```") == "SELECT * FROM customers"
    assert validate_sql("WITH t AS (SELECT 1 AS x) SELECT x FROM t").startswith("WITH")
    assert validate_sql("SELECT 'drop; table' AS note, joined_on AS created_at FROM customers")


def test_connection_blocks_writes(conn):
    with pytest.raises(sqlite3.DatabaseError):
        conn.execute("DELETE FROM customers")


def test_schema_has_all_tables(conn):
    s = get_schema_text(conn)
    for t in ("customers", "products", "orders", "order_items"):
        assert f"CREATE TABLE {t}" in s


def test_multi_table_join_aggregation(conn):
    sql = """SELECT p.category, SUM(oi.quantity * oi.unit_price) AS revenue
             FROM order_items oi JOIN products p ON p.id = oi.product_id
             JOIN orders o ON o.id = oi.order_id
             WHERE o.status != 'cancelled' GROUP BY p.category ORDER BY revenue DESC"""
    ans = ask("revenue by category", conn, get_schema_text(conn), FakeLLM(sql))
    assert ans.columns == ["category", "revenue"] and len(ans.rows) >= 3 and ans.attempts == 1


def test_self_correction_after_sql_error(conn):
    llm = FakeLLM("SELECT nope FROM customers", "SELECT COUNT(*) AS n FROM customers")
    ans = ask("how many customers", conn, get_schema_text(conn), llm)
    assert ans.attempts == 2 and ans.rows == [(40,)]
    assert llm.calls[1][1]


def test_unsafe_output_never_runs(conn):
    llm = FakeLLM("DELETE FROM customers", "DROP TABLE orders")
    with pytest.raises(AssistantError):
        ask("remove everyone", conn, get_schema_text(conn), llm)
    assert conn.execute("SELECT COUNT(*) FROM customers").fetchone()[0] == 40


def test_unanswerable(conn):
    with pytest.raises(AssistantError):
        ask("what's the weather", conn, get_schema_text(conn), FakeLLM("UNANSWERABLE"))
