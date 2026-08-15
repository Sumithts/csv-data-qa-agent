"""Run with: python -m pytest tests/ -v

Uses a stub LLMProvider (dependency-injected into CSVQAAgent) so these
tests run with zero network calls and zero API key — verifying the
agent's retry/error-handling logic in isolation from Groq.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd
import pytest

from src.agent import CSVQAAgent
from src.exceptions import NotADataQuestionError
from src.models import AnswerMode, ResultType
from src.schema import build_schema

CSV_PATH = Path(__file__).resolve().parent.parent / "data" / "sales_data.csv"


def test_build_schema_reports_correct_row_and_column_count() -> None:
    df = pd.DataFrame({"a": [1, 2, 3], "b": ["x", "y", "z"]})
    schema = build_schema(df)
    assert schema.row_count == 3
    assert {c.name for c in schema.columns} == {"a", "b"}


class StubProvider:
    """A fake LLMProvider that returns pre-scripted responses, in order."""

    def __init__(self, responses: list[tuple[str, str]], general_answer: str = "stub general answer") -> None:
        self._responses = iter(responses)
        self._general_answer = general_answer

    def generate_pandas_code(self, question, schema_context, previous_error=None):
        response = next(self._responses)
        if response == "NOT_A_DATA_QUESTION":
            raise NotADataQuestionError(question)
        return response

    def generate_general_answer(self, question, schema_context):
        return self._general_answer


def test_agent_succeeds_on_first_try() -> None:
    agent = CSVQAAgent(CSV_PATH, llm_provider=StubProvider([
        ("result = df['revenue'].sum()", "Sums revenue."),
    ]))
    qa = agent.ask("total revenue?")
    assert qa.success
    assert qa.attempts == 1
    assert qa.result_type == ResultType.SCALAR
    assert qa.mode == AnswerMode.CODE_EXECUTION


def test_agent_retries_after_runtime_error_then_succeeds() -> None:
    agent = CSVQAAgent(CSV_PATH, llm_provider=StubProvider([
        ("result = df['nonexistent_col'].sum()", "Bad column."),
        ("result = df['revenue'].sum()", "Sums revenue (fixed)."),
    ]))
    qa = agent.ask("total revenue?")
    assert qa.success
    assert qa.attempts == 2


def test_agent_fails_closed_on_unsafe_code_without_retry() -> None:
    agent = CSVQAAgent(CSV_PATH, llm_provider=StubProvider([
        ("import os\nresult = 1", "Malicious."),
        ("result = df['revenue'].sum()", "Should never be reached."),
    ]))
    qa = agent.ask("anything")
    assert not qa.success
    assert qa.attempts == 1  # no retry attempted for unsafe code
    assert "unsafe" in qa.error.lower()


def test_agent_falls_back_to_general_knowledge_after_exhausting_retries() -> None:
    """A question unrelated to the dataset should exhaust code-gen retries and
    still get answered — via the general-knowledge fallback — instead of
    just failing. This is what lets the agent handle *any* question."""
    agent = CSVQAAgent(CSV_PATH, llm_provider=StubProvider(
        responses=[
            ("result = df['nope'].sum()", ""),
            ("result = df['still_nope'].sum()", ""),
            ("result = df['nope_again'].sum()", ""),
        ],
        general_answer="Paris is the capital of France.",
    ))
    qa = agent.ask("What is the capital of France?")
    assert qa.success  # answered, just not from the dataset
    assert qa.mode == AnswerMode.GENERAL_KNOWLEDGE
    assert qa.result_type == ResultType.TEXT
    assert qa.explanation == "Paris is the capital of France."
    assert qa.code == ""  # no code was executed for the fallback answer

def test_agent_short_circuits_on_greeting_without_wasting_retries() -> None:
    """A greeting like "hi" should be flagged by the LLM as not-a-data-question
    and answered on attempt 1 — it should NOT burn through the retry budget
    or default to something misleading like `df.head()`."""
    agent = CSVQAAgent(CSV_PATH, llm_provider=StubProvider(
        responses=["NOT_A_DATA_QUESTION"],
        general_answer="Hi there! Ask me anything about the loaded dataset.",
    ))
    qa = agent.ask("haii")
    assert qa.success
    assert qa.attempts == 1  # no wasted codegen retries
    assert qa.mode == AnswerMode.GENERAL_KNOWLEDGE
    assert qa.code == ""
    assert qa.explanation == "Hi there! Ask me anything about the loaded dataset."
    
def test_agent_exhausts_code_retries_before_falling_back() -> None:
    """Confirms the agent genuinely tries the grounded code path first (all
    3 attempts) before ever reaching for the general-knowledge fallback —
    it doesn't give up early or skip the data-grounded attempt."""
    agent = CSVQAAgent(CSV_PATH, llm_provider=StubProvider([
        ("result = df['nope'].sum()", ""),
        ("result = df['still_nope'].sum()", ""),
        ("result = df['nope_again'].sum()", ""),
    ]))
    qa = agent.ask("total revenue?")
    assert qa.attempts == 3  # 1 initial + 2 retries (default max_codegen_retries)
    assert qa.mode == AnswerMode.GENERAL_KNOWLEDGE
    assert qa.success  # falls back rather than reporting failure
