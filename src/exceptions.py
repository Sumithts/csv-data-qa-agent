"""Custom exception hierarchy for the CSV Q&A Agent.

Using a typed hierarchy (rather than bare Exception/ValueError everywhere)
lets callers catch precisely what they mean to catch — e.g. the CLI/UI
layer can catch LLMProviderError to show "check your API key" without
accidentally swallowing a programming bug.
"""
from __future__ import annotations


class AgentError(Exception):
    """Base class for all errors raised by this package."""


class ConfigurationError(AgentError):
    """Raised when required configuration (e.g. an API key) is missing or invalid."""


class LLMProviderError(AgentError):
    """Raised when the underlying LLM API call fails (network, auth, rate limit, etc.)."""


class CodeGenerationError(AgentError):
    """Raised when the LLM's response cannot be parsed into runnable code."""


class UnsafeCodeError(AgentError):
    """Raised when generated code fails the static AST safety check."""


class SandboxExecutionError(AgentError):
    """Raised when generated code raises at runtime inside the sandbox."""


class DataLoadError(AgentError):
    """Raised when the target CSV/data file cannot be loaded or parsed."""


class NotADataQuestionError(AgentError):
    """Raised when the LLM determines the question isn't about the loaded
    dataset at all (greetings, small talk, off-topic questions) — lets the
    agent route straight to the general-knowledge path on attempt 1 instead
    of burning codegen retries writing pointless code like `df.head()`."""