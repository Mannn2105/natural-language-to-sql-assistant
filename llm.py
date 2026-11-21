"""LLM calls: natural language -> SQL, and result summaries."""
import json
import os

import anthropic

MODEL = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-5-5")

SQL_SYSTEM = """You convert questions into one SQLite SELECT query.
Rules:
- Use ONLY the tables and columns in the schema below. Join tables through the foreign keys when needed.
- Output a single SELECT (or WITH ... SELECT) statement and nothing else: no explanation, no markdown.
- Never write INSERT, UPDATE, DELETE, DROP, ALTER, CREATE or PRAGMA.
- Revenue = quantity * unit_price from order_items. Exclude orders with status 'cancelled' from revenue unless asked.
- Use SQLite date functions (strftime, date) for dates, and ORDER BY / LIMIT for "top" questions.
- If the question cannot be answered from this schema, output exactly: UNANSWERABLE

Schema:
{schema}"""

SUMMARY_SYSTEM = (
    "You explain database query results to a non-technical reader in 1-3 plain sentences. "
    "Use only the numbers and names present in the rows. Do not invent data. If there are no rows, say so."
)


class AnthropicLLM:
    def __init__(self, api_key: str | None = None, model: str = MODEL):
        self.client = anthropic.Anthropic(api_key=api_key or os.getenv("ANTHROPIC_API_KEY"))
        self.model = model

    def _complete(self, system: str, user: str, max_tokens: int) -> str:
        msg = self.client.messages.create(
            model=self.model, max_tokens=max_tokens, system=system,
            messages=[{"role": "user", "content": user}],
        )
        return "".join(b.text for b in msg.content if b.type == "text").strip()

    def generate_sql(self, question, schema, previous_sql=None, previous_error=None) -> str:
        user = f"Question: {question}"
        if previous_sql and previous_error:
            user += (f"\n\nYour previous query failed.\nQuery: {previous_sql}\nError: {previous_error}\n"
                     "Write a corrected query.")
        return self._complete(SQL_SYSTEM.format(schema=schema), user, 600)

    def summarize(self, question, sql, columns, rows) -> str:
        payload = json.dumps({"question": question, "sql": sql, "columns": columns, "rows": rows},
                             default=str)
        return self._complete(SUMMARY_SYSTEM, payload, 250)
