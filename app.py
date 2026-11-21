"""Streamlit UI for the Natural Language to SQL Assistant."""
import os

import pandas as pd
import streamlit as st

from assistant import AssistantError, ask
from db import create_database, get_readonly_connection, get_schema_text
from llm import AnthropicLLM

st.set_page_config(page_title="Natural Language to SQL Assistant", page_icon="🗄️", layout="wide")

EXAMPLES = [
    "Which 5 customers spent the most on delivered orders?",
    "Total revenue by product category",
    "How many orders were placed in each city?",
    "Monthly revenue for 2025, excluding cancelled orders",
    "Which products have never been ordered?",
]


@st.cache_resource
def get_db():
    create_database()
    conn = get_readonly_connection()
    return conn, get_schema_text(conn)


def set_question(q: str):
    st.session_state["question"] = q


conn, schema = get_db()

st.title("🗄️ Natural Language to SQL Assistant")
st.caption("Ask a question in plain English. The app writes a read-only SQL query, runs it, and explains the result.")

with st.sidebar:
    st.header("Setup")
    api_key = os.getenv("ANTHROPIC_API_KEY") or st.text_input("Anthropic API key", type="password")
    st.header("Try an example")
    for ex in EXAMPLES:
        st.button(ex, on_click=set_question, args=(ex,), use_container_width=True)
    with st.expander("Database schema"):
        st.code(schema, language="sql")

question = st.text_input("Your question", key="question", placeholder="e.g. Which city has the most customers?")

if st.button("Run", type="primary"):
    if not api_key:
        st.error("Add your Anthropic API key in the sidebar (or set ANTHROPIC_API_KEY).")
    else:
        try:
            with st.spinner("Writing and running the query..."):
                result = ask(question, conn, schema, AnthropicLLM(api_key=api_key))
        except AssistantError as exc:
            st.warning(str(exc))
        except Exception as exc:
            st.error(f"Something went wrong calling the model: {exc}")
        else:
            st.subheader("Summary")
            st.write(result.summary)
            st.subheader("Generated SQL")
            st.code(result.sql, language="sql")
            if result.attempts > 1:
                st.info("The first query failed, so the assistant corrected it automatically.")
            st.subheader(f"Results ({len(result.rows)} row{'s' if len(result.rows) != 1 else ''})")
            if result.rows:
                st.dataframe(pd.DataFrame(result.rows, columns=result.columns), use_container_width=True)
            else:
                st.write("No rows matched.")
            if result.truncated:
                st.caption("Showing the first 500 rows only.")
