"""LLM integration layer.

Defines an `LLMProvider` Protocol so the agent core depends on an
abstraction, not a concrete vendor SDK — swapping Groq for OpenAI,
Anthropic, or a local vLLM server means writing one new class, not
touching `agent.py`. `GroqProvider` is the implementation actually
used (per project requirements: Groq only), built on the OpenAI SDK
since Groq exposes an OpenAI-compatible endpoint.
"""
from __future__ import annotations

from typing import Protocol

from openai import APIError, APITimeoutError, OpenAI, RateLimitError
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from .config import settings
from .exceptions import CodeGenerationError, LLMProviderError, NotADataQuestionError
from .logging_config import get_logger

logger = get_logger(__name__)

# Sentinel the model returns when a question isn't actually about the
# dataset (greetings, small talk, "what can you do", off-topic questions).
# Without this, an under-specified prompt makes the LLM default to a
# harmless-looking but misleading guess like `result = df.head()` for
# something like "hi" — which then reports SUCCESS even though nothing
# was really answered.
NOT_DATA_MARKER = "NOT_DATA_QUESTION"

SYSTEM_PROMPT = f"""You are a senior data analyst assistant that answers questions \
about a pandas DataFrame called `df` by WRITING PYTHON CODE, not by guessing.

Rules:
- You are given the DataFrame's column names, dtypes, and a few sample rows.
- First decide: is this question actually asking something about the dataset \
  (its rows, columns, values, aggregates, comparisons, trends)?
- If it is NOT a data question — greetings ("hi", "hello"), small talk, \
  meta questions ("what can you do?"), or anything unrelated to the dataset — \
  respond with EXACTLY the single line `{NOT_DATA_MARKER}` and nothing else. \
  Do NOT write a code block, and do NOT default to something like `df.head()` \
  just to have an answer.
- Otherwise, write short, correct pandas code that computes the answer from `df`.
- Assign the final answer to a variable named `result` (a number, string, \
  list, or a small pandas DataFrame/Series — whichever fits the question).
- Do NOT import anything. `pd` (pandas) and `np` (numpy) are already available.
- Do NOT read/write files, access the network, or use eval/exec/open.
- Do NOT invent column names that are not in the schema provided.
- After the code, on a new line starting with `EXPLANATION:`, write ONE plain \
  English sentence explaining what the code computes.
- Return ONLY a python code block (```python ... ```) followed by the \
  EXPLANATION line. No other prose.
"""


GENERAL_SYSTEM_PROMPT = """You are a helpful, knowledgeable assistant embedded inside a data \
analysis tool. The user's question is NOT about the currently loaded dataset (it doesn't \
match its columns/subject matter), so answer it directly and helpfully from your own \
knowledge, the same way a general-purpose assistant would.

Rules:
- Be direct, accurate, and concise (a few sentences unless more detail is clearly needed).
- If you are not confident about a fact, say so rather than guessing.
- Do not pretend the answer came from the loaded dataset — it did not.
- Do not write code for this; just answer in plain natural language.
"""


class LLMProvider(Protocol):
    """Anything that can turn a question + schema into (code, explanation), and separately
    answer general questions in plain language, satisfies this."""

    def generate_pandas_code(
        self, question: str, schema_context: str, previous_error: str | None = None
    ) -> tuple[str, str]:
        ...

    def generate_general_answer(self, question: str, schema_context: str) -> str:
        ...


class GroqProvider:
    """LLMProvider implementation backed by Groq's free, OpenAI-compatible API."""

    def __init__(self) -> None:
        api_key = settings.require_groq_key()
        self._client = OpenAI(
            api_key=api_key,
            base_url=settings.groq_base_url,
            timeout=settings.request_timeout_seconds,
        )
        self._model = settings.groq_model

    @retry(
        retry=retry_if_exception_type((APITimeoutError, RateLimitError)),
        wait=wait_exponential(multiplier=1, min=1, max=8),
        stop=stop_after_attempt(3),
        reraise=True,
    )
    def _call_api_with_prompt(self, system_prompt: str, user_msg: str) -> str:
        try:
            response = self._client.chat.completions.create(
                model=self._model,
                temperature=settings.llm_temperature,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_msg},
                ],
            )
        except (APIError, APITimeoutError, RateLimitError) as exc:
            logger.error("Groq API call failed: %s", exc)
            raise LLMProviderError(f"Groq API call failed: {exc}") from exc

        content = response.choices[0].message.content
        if not content:
            raise LLMProviderError("Groq returned an empty response.")
        return content

    def _call_api(self, user_msg: str) -> str:
        return self._call_api_with_prompt(SYSTEM_PROMPT, user_msg)

    def generate_pandas_code(
        self, question: str, schema_context: str, previous_error: str | None = None
    ) -> tuple[str, str]:
        user_msg = f"DataFrame schema and sample:\n{schema_context}\n\nQuestion: {question}"
        if previous_error:
            user_msg += f"\n\nYour previous code raised this error, fix it:\n{previous_error}"

        raw_text = self._call_api(user_msg)
        if raw_text.strip().upper().startswith(NOT_DATA_MARKER):
            raise NotADataQuestionError(question)
        return _parse_code_and_explanation(raw_text)

    def generate_general_answer(self, question: str, schema_context: str) -> str:
        """Answers a question that isn't about the loaded dataset — general knowledge,
        conversation, anything — the same way a general-purpose assistant would.
        """
        user_msg = (
            f"(For context only — the loaded dataset has this schema, but the question "
            f"below doesn't appear to be about it:\n{schema_context}\n)\n\n"
            f"Question: {question}"
        )
        return self._call_api_with_prompt(GENERAL_SYSTEM_PROMPT, user_msg).strip()


def _parse_code_and_explanation(text: str) -> tuple[str, str]:
    if "```python" in text:
        code = text.split("```python", 1)[1].split("```", 1)[0].strip()
    elif "```" in text:
        code = text.split("```", 1)[1].split("```", 1)[0].strip()
    else:
        code = text.strip()

    if not code:
        raise CodeGenerationError(f"Could not extract any code from LLM response:\n{text}")

    explanation = ""
    for line in text.splitlines():
        if line.strip().upper().startswith("EXPLANATION:"):
            explanation = line.split(":", 1)[1].strip()
            break
    if not explanation:
        explanation = "Computed directly from the dataset via pandas."

    return code, explanation