"""Executes LLM-generated pandas code against the real DataFrame in a
restricted sandbox, so the agent's answers are *computed*, never guessed.

Safety model (adequate for a local CLI/Streamlit tool, not a hardened
multi-tenant sandbox — see README "Tradeoffs" for the production version):

  1. Static AST allow-list: reject any code containing imports, dunder
     attribute access, or known-dangerous names BEFORE it ever executes.
  2. Restricted builtins: only a small safe subset of Python builtins is
     exposed to the executed code (no `open`, `eval`, `exec`, `__import__`).
  3. Isolated namespace + defensive copy: the code only ever sees `df`
     (a copy), `pd`, and `np` — never the host process's globals, and it
     cannot mutate the caller's original DataFrame.
"""
from __future__ import annotations

import ast
import builtins as _builtins
from typing import Any, Final

import numpy as np
import pandas as pd

from .exceptions import SandboxExecutionError, UnsafeCodeError
from .logging_config import get_logger

logger = get_logger(__name__)

_FORBIDDEN_NAMES: Final[frozenset[str]] = frozenset({
    "__import__", "eval", "exec", "compile", "open", "input",
    "exit", "quit", "help", "globals", "locals", "vars", "dir",
    "getattr", "setattr", "delattr", "breakpoint",
})

_FORBIDDEN_MODULES: Final[frozenset[str]] = frozenset({
    "os", "sys", "subprocess", "shutil", "socket", "requests",
    "pathlib", "importlib", "ctypes", "pickle", "multiprocessing",
})

_SAFE_BUILTIN_NAMES: Final[tuple[str, ...]] = (
    "len", "range", "min", "max", "sum", "sorted", "list", "dict",
    "set", "tuple", "str", "int", "float", "bool", "round", "abs",
    "enumerate", "zip", "map", "filter", "any", "all", "print",
)


def validate_code(code: str) -> None:
    """Statically rejects unsafe code before it is ever executed.

    Raises:
        UnsafeCodeError: if the code contains imports, dunder access,
            or any forbidden name/module reference.
    """
    try:
        tree = ast.parse(code, mode="exec")
    except SyntaxError as exc:
        raise UnsafeCodeError(f"Code does not parse: {exc}") from exc

    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            raise UnsafeCodeError("Imports are not allowed in generated code.")
        if isinstance(node, ast.Attribute) and node.attr.startswith("__"):
            raise UnsafeCodeError(f"Dunder attribute access is not allowed: {node.attr}")
        if isinstance(node, ast.Name) and node.id in _FORBIDDEN_NAMES:
            raise UnsafeCodeError(f"Use of '{node.id}' is not allowed.")
        if isinstance(node, ast.Name) and node.id in _FORBIDDEN_MODULES:
            raise UnsafeCodeError(f"Reference to module '{node.id}' is not allowed.")


def _build_safe_builtins() -> dict[str, Any]:
    return {name: getattr(_builtins, name) for name in _SAFE_BUILTIN_NAMES}


def run_pandas_code(code: str, df: pd.DataFrame) -> Any:
    """Validates and executes LLM-generated code against a copy of `df`.

    The code MUST assign its final answer to a variable named `result`.

    Args:
        code: The pandas code to execute (already checked by `validate_code`).
        df: The source DataFrame. A copy is passed into the sandbox so
            generated code can never mutate the caller's data.

    Returns:
        The value bound to `result` inside the executed code.

    Raises:
        UnsafeCodeError: if the code fails the static safety check.
        SandboxExecutionError: if the code raises at runtime, or fails
            to assign a `result` variable.
    """
    validate_code(code)

    safe_globals: dict[str, Any] = {
        "__builtins__": _build_safe_builtins(),
        "pd": pd,
        "np": np,
    }
    safe_locals: dict[str, Any] = {"df": df.copy()}

    try:
        exec(code, safe_globals, safe_locals)  # noqa: S102 — deliberately sandboxed, see module docstring
    except Exception as exc:  # noqa: BLE001 — any runtime error from arbitrary code is expected here
        logger.debug("Sandboxed code raised: %s", exc)
        raise SandboxExecutionError(f"{type(exc).__name__}: {exc}") from exc

    if "result" not in safe_locals:
        raise SandboxExecutionError("Generated code did not assign a `result` variable.")

    return safe_locals["result"]
