"""Structured logging setup, shared by the CLI and the Streamlit UI.

Uses `rich` for readable, colorized console logs (industry-standard
alternative to bare `print()` — gives timestamps, log levels, and
tracebacks for free).
"""
from __future__ import annotations

import logging

from rich.logging import RichHandler

from .config import settings

_CONFIGURED = False


def setup_logging() -> None:
    """Idempotent — safe to call multiple times (e.g. once per Streamlit rerun)."""
    global _CONFIGURED
    if _CONFIGURED:
        return

    logging.basicConfig(
        level=settings.log_level,
        format="%(message)s",
        datefmt="[%X]",
        handlers=[RichHandler(rich_tracebacks=True, show_path=False)],
    )
    _CONFIGURED = True


def get_logger(name: str) -> logging.Logger:
    setup_logging()
    return logging.getLogger(name)
