"""Typed domain models for the CSV Q&A Agent.

Using pydantic models (rather than loose dicts) gives us:
  - validation at the boundary (a malformed LLM response fails loudly)
  - free, correct JSON serialisation for the batch/UI output
  - self-documenting types for anyone reading the code
"""
from __future__ import annotations

from datetime import UTC, datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class ColumnInfo(BaseModel):
    """Metadata about a single DataFrame column, used to ground the LLM prompt."""

    name: str
    dtype: str
    sample_values: list[Any] = Field(default_factory=list)


class DatasetSchema(BaseModel):
    """A snapshot of a DataFrame's shape, used as grounding context for code generation."""

    row_count: int
    columns: list[ColumnInfo]
    preview_markdown: str = Field(description="A small rendered sample of the data (head rows)")

    def as_prompt_context(self) -> str:
        """Renders the schema as plain text suitable for an LLM prompt."""
        lines = [f"Rows: {self.row_count}", "Columns:"]
        for col in self.columns:
            lines.append(f"  - {col.name} ({col.dtype}), e.g. {col.sample_values}")
        lines.append("\nSample rows:")
        lines.append(self.preview_markdown)
        return "\n".join(lines)


class ResultType(str, Enum):
    """How to render a QAResult's `result` value in the UI/CLI."""

    SCALAR = "scalar"
    LIST = "list"
    DICT = "dict"
    TABLE = "table"
    TEXT = "text"
    UNKNOWN = "unknown"


class AnswerMode(str, Enum):
    """How a QAResult's answer was produced.

    CODE_EXECUTION: the question was answered by generating and running
        real pandas code against the dataset (the grounded, hallucination-
        proof path — used for anything about the data).
    GENERAL_KNOWLEDGE: the question wasn't about the loaded dataset (e.g.
        "what's the capital of France?"), so the LLM answered directly,
        the same way a general assistant would. No code was executed and
        no claim is made that this came from the dataset.
    """

    CODE_EXECUTION = "code_execution"
    GENERAL_KNOWLEDGE = "general_knowledge"


class QAResult(BaseModel):
    """The full record of one question -> code -> execution -> answer cycle."""

    model_config = {"arbitrary_types_allowed": True}

    question: str
    code: str = ""
    explanation: str = ""
    result: Any = None
    result_type: ResultType = ResultType.UNKNOWN
    mode: AnswerMode = AnswerMode.CODE_EXECUTION
    success: bool = False
    attempts: int = 0
    error: str = ""
    from_cache: bool = False
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))

    def to_json_dict(self) -> dict[str, Any]:
        """A JSON-serialisable dict (pandas objects are already normalised before this is set)."""
        return self.model_dump(mode="json")