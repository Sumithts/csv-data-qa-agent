"""CSVQAAgent — the Input -> Think -> Act -> Output loop.

  Input:  a plain-English question + a loaded CSV
  Think:  the LLM provider turns the question into pandas code, grounded
          in the real schema (never guesses a number directly)
  Act:    the code runs in a sandbox against the real DataFrame
  Output: a QAResult — natural-language answer backed by the actual
          computed value, with the code and raw result shown so nothing
          is hidden or hallucinated
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd
from pandas.api.types import is_scalar

from .config import settings
from .exceptions import DataLoadError, NotADataQuestionError, SandboxExecutionError, UnsafeCodeError
from .llm_client import GroqProvider, LLMProvider
from .logging_config import get_logger
from .models import AnswerMode, QAResult, ResultType
from .query_cache import SemanticQueryCache
from .sandbox_executor import run_pandas_code
from .schema import build_schema

logger = get_logger(__name__)


class CSVQAAgent:
    """Answers natural-language questions about a CSV by generating and
    executing real pandas code, with one automatic self-correction retry
    on runtime errors.
    """

    def __init__(
        self,
        csv_path: str | Path,
        llm_provider: LLMProvider | None = None,
        query_cache: SemanticQueryCache | None = None,
    ) -> None:
        self.csv_path = Path(csv_path)
        self.df = self._load_csv(self.csv_path)
        self.schema = build_schema(self.df)
        # Dependency injection: defaults to Groq, but any LLMProvider can be
        # passed in (e.g. a stub in tests) without touching this class.
        self._llm: LLMProvider = llm_provider or GroqProvider()
        # Semantic cache: skips the codegen LLM call for a paraphrase of a
        # question we've already solved. Off by default in tests (None ->
        # a fresh empty cache) so nothing here has hidden network/model
        # dependencies unless the caller opts in.
        self._cache = query_cache if query_cache is not None else SemanticQueryCache()
        logger.info("Loaded %s (%d rows, %d columns)", self.csv_path, len(self.df), len(self.df.columns))

    @staticmethod
    def _load_csv(path: Path) -> pd.DataFrame:
        if not path.exists():
            raise DataLoadError(f"File not found: {path}")
        try:
            if path.suffix.lower() in (".xlsx", ".xls"):
                return pd.read_excel(path)
            return pd.read_csv(path)
        except (pd.errors.ParserError, UnicodeDecodeError, ValueError) as exc:
            raise DataLoadError(f"Could not parse file at {path}: {exc}") from exc

    def ask(self, question: str) -> QAResult:
        """Runs one full Input -> Think -> Act -> Output cycle for a single question.

        Tries the grounded pandas-code path first (never guesses a number for
        data questions). If that fails after all retries — most often because
        the question isn't actually about the loaded dataset — falls back to
        a direct, clearly-labelled general-knowledge answer from the LLM, so
        the agent can respond to *any* question, not just ones about the CSV.
        """
        qa = QAResult(question=question)

        # Semantic cache: if a paraphrase of this question has already been
        # solved, reuse the CODE (skipping the codegen LLM call entirely)
        # but still EXECUTE it fresh against the current DataFrame — so a
        # cache hit never returns a stale or hallucinated number, only a
        # skipped LLM call.
        cached = self._cache.lookup(question)
        if cached is not None:
            try:
                result = run_pandas_code(cached.code, self.df)
            except (UnsafeCodeError, SandboxExecutionError) as exc:
                # Cached code no longer works against this data (e.g. a
                # different CSV was uploaded) — fall through to the normal
                # live-codegen path below instead of failing.
                logger.info("Cached code failed to re-execute (%s), regenerating.", exc)
            else:
                qa.code = cached.code
                qa.explanation = cached.explanation
                qa.result = _normalize_result(result)
                qa.result_type = _classify_result(result)
                qa.mode = AnswerMode.CODE_EXECUTION
                qa.success = True
                qa.attempts = 1
                qa.from_cache = True
                return qa

        previous_error: str | None = None
        max_attempts = settings.max_codegen_retries + 1

        for attempt in range(1, max_attempts + 1):
            qa.attempts = attempt
            logger.debug("Attempt %d/%d for question: %s", attempt, max_attempts, question)

            try:
                code, explanation = self._llm.generate_pandas_code(
                    question, self.schema.as_prompt_context(), previous_error
                )
            except NotADataQuestionError:
                # The model itself flagged this as not about the dataset
                # (greeting, small talk, off-topic) — go straight to the
                # general-knowledge path on attempt 1 rather than wasting
                # retries and rather than silently defaulting to df.head().
                logger.info("Question flagged as not about the dataset: %s", question)
                answer = self._llm.generate_general_answer(question, self.schema.as_prompt_context())
                qa.code = ""
                qa.explanation = answer
                qa.result = None
                qa.result_type = ResultType.TEXT
                qa.mode = AnswerMode.GENERAL_KNOWLEDGE
                qa.success = True
                qa.error = ""
                return qa

            qa.code = code
            qa.explanation = explanation

            try:
                result = run_pandas_code(code, self.df)
            except UnsafeCodeError as exc:
                # Fail closed immediately — never retry unsafe code, and never
                # fall back to general knowledge for something that tried to
                # do something unsafe.
                logger.warning("Rejected unsafe generated code: %s", exc)
                qa.error = f"Rejected unsafe code: {exc}"
                qa.success = False
                return qa
            except SandboxExecutionError as exc:
                logger.info("Attempt %d failed, will retry: %s", attempt, exc)
                previous_error = str(exc)
                qa.error = previous_error
                continue

            qa.result = _normalize_result(result)
            qa.result_type = _classify_result(result)
            qa.mode = AnswerMode.CODE_EXECUTION
            qa.success = True
            qa.error = ""
            self._cache.store(question, code, explanation)
            return qa

        # Code generation could not answer this from the dataset after every
        # retry — fall back to a general-knowledge answer instead of just
        # reporting failure, so the agent can handle *any* question.
        logger.info("Falling back to general-knowledge answer for: %s", question)
        answer = self._llm.generate_general_answer(question, self.schema.as_prompt_context())
        qa.code = ""
        qa.explanation = answer
        qa.result = None
        qa.result_type = ResultType.TEXT
        qa.mode = AnswerMode.GENERAL_KNOWLEDGE
        qa.success = True
        qa.error = ""
        return qa


def _classify_result(value: object) -> ResultType:
    if isinstance(value, pd.DataFrame):
        return ResultType.TABLE
    if isinstance(value, pd.Series):
        return ResultType.DICT
    if isinstance(value, dict):
        return ResultType.DICT
    if isinstance(value, (list, tuple)):
        return ResultType.LIST
    if is_scalar(value):
        return ResultType.SCALAR
    return ResultType.UNKNOWN


def _normalize_result(value: object) -> object:
    """Converts pandas/numpy objects into JSON- and Streamlit-friendly plain Python types."""
    if isinstance(value, pd.DataFrame):
        return value.to_dict(orient="records")
    if isinstance(value, pd.Series):
        return value.to_dict()
    if hasattr(value, "item"):  # numpy scalar (int64, float64, bool_, ...)
        return value.item()
    return value