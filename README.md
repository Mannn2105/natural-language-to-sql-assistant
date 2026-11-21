# Natural Language to SQL Assistant

A Streamlit application that converts plain-English questions into SQLite queries, executes them through a read-only database connection, and explains the returned results.

**Tech stack:** Python · Anthropic API · SQLite · SQL · Streamlit · Pandas · Pytest

## Features
- Ask questions in natural language, such as: “Which 5 customers spent the most on delivered orders?”
- Generate SQL using the database schema as context.
- Support filtering, sorting, aggregations, and multi-table joins.
- Validate generated SQL before execution.
- Execute queries through a read-only SQLite connection.
- Display the generated SQL, result table, and a plain-English summary.
- Retry once when a generated query fails, using the error as correction context.
- Include a synthetic shop database for local experimentation.

## Safety and query controls
1. The LLM prompt requests a single `SELECT` or `WITH ... SELECT` statement.
2. `sql_guard.py` rejects non-read-only statements and multiple SQL statements.
3. SQLite is opened in read-only mode.
4. A SQLite authorizer restricts database operations to reading data.
5. Query execution has a 5-second timeout and returns at most 500 rows.

Generated SQL can still be logically incorrect. Review the displayed SQL and results before relying on them. The safeguards are designed for this sample application and are not a substitute for a security review before production use.

## Project structure
```text
nl2sql-assistant/
├── app.py
├── assistant.py
├── db.py
├── llm.py
├── sql_guard.py
├── test_nl2sql.py
├── requirements.txt
├── .env.example
└── .gitignore
```

## Getting started

### 1. Clone the repository
```bash
git clone https://github.com/Mannn2105/natural-language-to-sql-assistant.git
cd natural-language-to-sql-assistant
```

### 2. Create and activate a virtual environment

**Windows PowerShell**
```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

**macOS / Linux**
```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure your Anthropic API key
The app reads `ANTHROPIC_API_KEY` from the environment. Copy `.env.example` to `.env` for reference, then set the key in your terminal.

**Windows PowerShell**
```powershell
$env:ANTHROPIC_API_KEY="your_api_key_here"
```

**macOS / Linux**
```bash
export ANTHROPIC_API_KEY="your_api_key_here"
```

Optionally set `ANTHROPIC_MODEL` to choose a model available to your Anthropic account.

### 5. Run the application
```bash
streamlit run app.py
```

## Run tests
```bash
pytest -q
```
The test suite covers SQL validation, read-only enforcement, joins, and retry/self-correction using a fake LLM, so tests do not require an API key.

## Example questions
- Which 5 customers spent the most on delivered orders?
- What is the total revenue by product category?
- How many orders were placed in each city?
- What was the monthly revenue in 2025, excluding cancelled orders?
- Which products have never been ordered?

## Current limitations
- The included sample database uses synthetic data.
- SQLite is the supported database engine.
- The app requires an Anthropic API key for live question answering.
- LLM-generated SQL may be syntactically valid but return an unintended result; inspect the SQL before using the output.

## Future improvements
- Add support for user-provided databases with explicit connection controls.
- Add query explanation and schema visualization.
- Add evaluation datasets for measuring SQL accuracy.
- Add deployment instructions and application screenshots.
