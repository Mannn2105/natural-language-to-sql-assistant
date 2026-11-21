"""Orchestration: question -> SQL -> validate -> execute (read-only) -> summary."""
import sqlite3
import time
from dataclasses import dataclass, field

from sql_guard import UnsafeSQLError, validate_sql

MAX_ROWS = 500
MAX_ATTEMPTS = 2
TIMEOUT_SECONDS = 5


class AssistantError(Exception):
    """A user-facing error."""


@dataclass
class Answer:
    question: str
    sql: str
    columns: list
    rows: list
    truncated: bool
    summary: str
    attempts: int = 1
    notes: list = field(default_factory=list)


def run_query(conn: sqlite3.Connection, sql: str):
    """Execute with a time limit and a row cap."""
    deadline = time.monotonic() + TIMEOUT_SECONDS
    conn.set_progress_handler(lambda: 1 if time.monotonic() > deadline else 0, 10000)
    try:
        cur = conn.execute(sql)
        columns = [d[0] for d in cur.description] if cur.description else []
        rows = cur.fetchmany(MAX_ROWS + 1)
    finally:
        conn.set_progress_handler(None, 0)
    return columns, rows[:MAX_ROWS], len(rows) > MAX_ROWS


def ask(question: str, conn: sqlite3.Connection, schema: str, llm) -> Answer:
    question = (question or "").strip()
    if not question:
        raise AssistantError("Please type a question.")
    last_sql = last_error = None
    notes = []
    for attempt in range(1, MAX_ATTEMPTS + 1):
        raw = llm.generate_sql(question, schema, last_sql, last_error)
        if raw.strip().upper().startswith("UNANSWERABLE"):
            raise AssistantError("That question can't be answered from the tables in this database.")
        try:
            sql = validate_sql(raw)
            columns, rows, truncated = run_query(conn, sql)
        except (UnsafeSQLError, sqlite3.Error) as exc:
            last_sql, last_error = raw, str(exc)
            notes.append(f"Attempt {attempt} failed: {exc}")
            continue
        try:
            summary = llm.summarize(question, sql, columns, rows[:20])
        except Exception:
            summary = f"The query returned {len(rows)} row(s)."
        return Answer(question, sql, columns, rows, truncated, summary, attempt, notes)
    raise AssistantError(f"Could not produce a valid query after {MAX_ATTEMPTS} attempts. Last error: {last_error}")
