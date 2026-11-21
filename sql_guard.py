"""Validation of LLM-generated SQL before it touches the database."""
import re


class UnsafeSQLError(ValueError):
    """Raised when generated SQL is not a single, read-only SELECT statement."""


_FENCE = re.compile(r"^```(?:sql)?\s*|\s*```$", re.I)
# string literals, quoted identifiers, line comments and block comments
_STRIP = re.compile(r"'(?:[^']|'')*'|\"(?:[^\"]|\"\")*\"|--[^\n]*|/\*.*?\*/", re.S)
_FORBIDDEN = re.compile(
    r"\b(insert|update|delete|drop|alter|create|truncate|attach|detach|pragma|vacuum|reindex|load_extension)\b",
    re.I,
)


def clean_sql(raw: str) -> str:
    sql = _FENCE.sub("", raw.strip()).strip()
    return sql.rstrip(";").strip()


def validate_sql(raw: str) -> str:
    """Return the cleaned SQL, or raise UnsafeSQLError."""
    sql = clean_sql(raw or "")
    if not sql:
        raise UnsafeSQLError("The model returned an empty query.")
    checkable = _STRIP.sub(" ", sql)
    if ";" in checkable:
        raise UnsafeSQLError("Only a single SQL statement is allowed.")
    if not re.match(r"^\s*(select|with)\b", checkable, re.I):
        raise UnsafeSQLError("Only SELECT queries are allowed.")
    bad = _FORBIDDEN.search(checkable)
    if bad:
        raise UnsafeSQLError(f"Forbidden keyword in query: {bad.group(1).upper()}.")
    return sql
