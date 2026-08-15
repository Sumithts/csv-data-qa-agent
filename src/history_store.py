"""src/history_store.py — SQLite-backed chat sessions.

Each "chat" is now a named, timestamped session (like a ChatGPT thread),
not one continuous history per dataset. A session can be renamed or
deleted independently. Every message inside a session keeps its own
timestamp (via QAResult.timestamp), so the UI can show exactly when
each question was asked.

Auto-migration: if an old-schema `qa_history` table (one flat history
per dataset, no sessions) is found on disk, its rows are migrated into
one "Imported chat" session per dataset on first run — no data is lost,
and no manual DB surgery is required.
"""
from __future__ import annotations

import json
import sqlite3
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import pandas as pd

from .models import AnswerMode, QAResult, ResultType

_DB_PATH = Path("data/history.db")

def _json_safe(value):
    """Convert pandas/NumPy values into JSON-serializable Python values."""
    if isinstance(value, dict):
        return {str(_json_safe(k)): _json_safe(v) for k, v in value.items()}

    if isinstance(value, (list, tuple)):
        return [_json_safe(v) for v in value]

    if isinstance(value, pd.Period):
        return str(value)

    if isinstance(value, pd.Timestamp):
        return value.isoformat()

    if isinstance(value, np.integer):
        return int(value)

    if isinstance(value, np.floating):
        return float(value)

    if isinstance(value, np.bool_):
        return bool(value)

    if value is None:
        return None

    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass

    return value


_SESSIONS_SCHEMA = """
CREATE TABLE IF NOT EXISTS chat_sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    dataset TEXT NOT NULL,
    name TEXT NOT NULL,
    created_at TEXT NOT NULL
);
"""

_HISTORY_SCHEMA = """
CREATE TABLE IF NOT EXISTS qa_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id INTEGER NOT NULL,
    question TEXT NOT NULL,
    code TEXT NOT NULL DEFAULT '',
    explanation TEXT NOT NULL DEFAULT '',
    result_json TEXT,
    result_type TEXT NOT NULL,
    mode TEXT NOT NULL,
    success INTEGER NOT NULL,
    attempts INTEGER NOT NULL DEFAULT 0,
    error TEXT NOT NULL DEFAULT '',
    from_cache INTEGER NOT NULL DEFAULT 0,
    timestamp TEXT NOT NULL
);
"""


def _table_columns(conn: sqlite3.Connection, table: str) -> list[str]:
    return [row[1] for row in conn.execute(f"PRAGMA table_info({table})")]


def _migrate_if_needed(conn: sqlite3.Connection) -> None:
    """Migrates an old/partially-migrated qa_history table (still carrying
    a legacy `dataset NOT NULL` column) onto the clean session-based
    schema, preserving every existing row.

    Trigger is the presence of the `dataset` column, not the absence of
    `session_id` — a prior partial migration can add `session_id` via
    ALTER TABLE without ever being able to remove `dataset`'s NOT NULL
    constraint (SQLite can't alter a column's constraints in place), so
    checking for `session_id` alone is not a reliable "already migrated"
    signal and can leave `dataset` stranded as NOT NULL forever. This
    version rebuilds the table from scratch onto the clean schema, which
    is idempotent: once `dataset` is gone, re-running this is a no-op.
    """
    tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    if "qa_history" not in tables:
        return
    cols = _table_columns(conn, "qa_history")
    if "dataset" not in cols:
        return  # already on the clean schema — nothing to do

    if "session_id" not in cols:
        conn.execute("ALTER TABLE qa_history ADD COLUMN session_id INTEGER")

    unmigrated_datasets = [
        r[0] for r in conn.execute(
            "SELECT DISTINCT dataset FROM qa_history WHERE session_id IS NULL"
        )
    ]
    for ds in unmigrated_datasets:
        cur = conn.execute(
            "INSERT INTO chat_sessions (dataset, name, created_at) VALUES (?, ?, ?)",
            (ds, "Imported chat", datetime.now(UTC).isoformat()),
        )
        session_id = cur.lastrowid
        conn.execute(
            "UPDATE qa_history SET session_id = ? WHERE dataset = ? AND session_id IS NULL",
            (session_id, ds),
        )

    conn.execute("ALTER TABLE qa_history RENAME TO qa_history_old")
    conn.execute(_HISTORY_SCHEMA)
    conn.execute(
        """INSERT INTO qa_history
           (id, session_id, question, code, explanation, result_json,
            result_type, mode, success, attempts, error, from_cache, timestamp)
           SELECT id, session_id, question, code, explanation, result_json,
                  result_type, mode, success, attempts, error, from_cache, timestamp
           FROM qa_history_old"""
    )
    conn.execute("DROP TABLE qa_history_old")
    conn.commit()


def _connect() -> sqlite3.Connection:
    _DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(_DB_PATH)
    conn.execute(_SESSIONS_SCHEMA)
    conn.execute(_HISTORY_SCHEMA)
    _migrate_if_needed(conn)
    return conn


def _default_session_name() -> str:
    return f"Chat — {datetime.now().strftime('%b %d, %Y %I:%M %p')}"


def create_session(dataset: str, name: str | None = None) -> int:
    """Creates a new named chat session for a dataset. Returns the session id."""
    conn = _connect()
    try:
        cur = conn.execute(
            "INSERT INTO chat_sessions (dataset, name, created_at) VALUES (?, ?, ?)",
            (dataset, name or _default_session_name(), datetime.now(UTC).isoformat()),
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def list_sessions(dataset: str) -> list[dict]:
    """Lists all chat sessions for a dataset, newest first, each with a message count."""
    conn = _connect()
    try:
        rows = conn.execute(
            """SELECT s.id, s.name, s.created_at, COUNT(h.id) AS message_count
               FROM chat_sessions s
               LEFT JOIN qa_history h ON h.session_id = s.id
               WHERE s.dataset = ?
               GROUP BY s.id
               ORDER BY s.created_at DESC""",
            (dataset,),
        ).fetchall()
    finally:
        conn.close()
    return [
        {"id": r[0], "name": r[1], "created_at": r[2], "message_count": r[3]}
        for r in rows
    ]


def rename_session(session_id: int, new_name: str) -> None:
    conn = _connect()
    try:
        conn.execute("UPDATE chat_sessions SET name = ? WHERE id = ?", (new_name.strip(), session_id))
        conn.commit()
    finally:
        conn.close()


def delete_session(session_id: int) -> None:
    """Deletes a chat session and every message inside it."""
    conn = _connect()
    try:
        conn.execute("DELETE FROM qa_history WHERE session_id = ?", (session_id,))
        conn.execute("DELETE FROM chat_sessions WHERE id = ?", (session_id,))
        conn.commit()
    finally:
        conn.close()


def save(session_id: int, qa: QAResult) -> None:
    """Persists one Q&A exchange inside the given session."""
    conn = _connect()
    try:
        conn.execute(
            """INSERT INTO qa_history
               (session_id, question, code, explanation, result_json, result_type,
                mode, success, attempts, error, from_cache, timestamp)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                session_id,
                qa.question,
                qa.code,
                qa.explanation,
                json.dumps(_json_safe(qa.result)),
                qa.result_type.value,
                qa.mode.value,
                int(qa.success),
                qa.attempts,
                qa.error,
                int(qa.from_cache),
                qa.timestamp.isoformat(),
            ),
        )
        conn.commit()
    finally:
        conn.close()


def load_session(session_id: int) -> list[QAResult]:
    """Loads every Q&A exchange in a session, oldest first."""
    conn = _connect()
    try:
        rows = conn.execute(
            """SELECT question, code, explanation, result_json, result_type,
                      mode, success, attempts, error, from_cache, timestamp
               FROM qa_history WHERE session_id = ? ORDER BY id ASC""",
            (session_id,),
        ).fetchall()
    finally:
        conn.close()

    history: list[QAResult] = []
    for row in rows:
        (question, code, explanation, result_json, result_type,
         mode, success, attempts, error, from_cache, timestamp) = row
        history.append(
            QAResult(
                question=question,
                code=code,
                explanation=explanation,
                result=json.loads(result_json) if result_json else None,
                result_type=ResultType(result_type),
                mode=AnswerMode(mode),
                success=bool(success),
                attempts=attempts,
                error=error,
                from_cache=bool(from_cache),
                timestamp=datetime.fromisoformat(timestamp),
            )
        )
    return history
