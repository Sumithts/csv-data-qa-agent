"""src/query_cache.py — semantic cache for generated pandas code.

This is NOT classic RAG over the dataset's content. The dataset is
structured/numeric, so there's no unstructured text to retrieve, and the
LLM's job here is writing CODE, not retrieving passages. What genuinely
applies is RAG's underlying mechanism — embed + similarity search —
pointed at a different target: a cache of questions we've already
solved, so a paraphrase of a question we've seen before skips the
code-generation LLM call entirely.

Why this can never return a stale or hallucinated number:
  - Only the CODE-GENERATION step is skipped on a cache hit. The cached
    CODE is still re-executed against the CURRENT DataFrame in the
    sandbox every time, so the computed value is always fresh — even if
    the underlying CSV changed since the code was first cached.
  - A hit requires high similarity (default 0.90), so "average revenue
    by region" and "avg revenue per region" hit the cache, but "average
    revenue by region" vs. "average PROFIT by region" do not.

Degrades gracefully: uses sentence-transformers embeddings if installed
(better paraphrase matching), otherwise falls back to difflib fuzzy
string matching so the agent still works with zero extra dependencies —
just a slightly less forgiving cache.
"""
from __future__ import annotations

import difflib
import json
from dataclasses import dataclass
from pathlib import Path

from .logging_config import get_logger

logger = get_logger(__name__)

# Two separate thresholds because the two matching strategies aren't
# equally forgiving: embeddings understand meaning ("total revenue" ~=
# "sum of all sales"), difflib only understands character overlap, so it
# needs a lower bar to catch anything beyond near-identical phrasing —
# and even then it won't catch true paraphrases with different word
# order (that's the honest limitation of the no-dependency fallback).
_EMBEDDING_SIMILARITY_THRESHOLD = 0.90
_FUZZY_SIMILARITY_THRESHOLD = 0.85

try:
    import numpy as np
    from sentence_transformers import SentenceTransformer

    _model = SentenceTransformer("all-MiniLM-L6-v2")
    _EMBEDDINGS_AVAILABLE = True
    logger.info("Query cache: using sentence-transformers embeddings.")
except ImportError:
    _EMBEDDINGS_AVAILABLE = False
    logger.info(
        "Query cache: sentence-transformers not installed, falling back to "
        "fuzzy string matching. `pip install sentence-transformers` for "
        "better paraphrase matching."
    )


@dataclass
class CacheEntry:
    question: str
    code: str
    explanation: str
    embedding: list[float] | None = None


class SemanticQueryCache:
    """Caches question -> (code, explanation) so a paraphrase of a
    previously-answered question skips the codegen LLM call."""

    def __init__(self, persist_path: str | Path | None = None) -> None:
        self._entries: list[CacheEntry] = []
        self._persist_path = Path(persist_path) if persist_path else None
        if self._persist_path and self._persist_path.exists():
            self._load()

    def lookup(self, question: str) -> CacheEntry | None:
        if not self._entries:
            return None
        return self._lookup_by_embedding(question) if _EMBEDDINGS_AVAILABLE else self._lookup_by_fuzzy_match(question)

    def store(self, question: str, code: str, explanation: str) -> None:
        embedding = _model.encode(question).tolist() if _EMBEDDINGS_AVAILABLE else None
        self._entries.append(CacheEntry(question, code, explanation, embedding))
        if self._persist_path:
            self._save()

    def _lookup_by_embedding(self, question: str) -> CacheEntry | None:
        query_vec = np.array(_model.encode(question))
        best, best_score = None, 0.0
        for entry in self._entries:
            vec = np.array(entry.embedding)
            score = float(query_vec @ vec / (np.linalg.norm(query_vec) * np.linalg.norm(vec) + 1e-9))
            if score > best_score:
                best, best_score = entry, score
        if best and best_score >= _EMBEDDING_SIMILARITY_THRESHOLD:
            logger.info("Cache hit (embedding similarity %.3f) for: %s", best_score, question)
            return best
        return None

    def _lookup_by_fuzzy_match(self, question: str) -> CacheEntry | None:
        best, best_score = None, 0.0
        norm_q = question.strip().lower()
        for entry in self._entries:
            score = difflib.SequenceMatcher(None, norm_q, entry.question.strip().lower()).ratio()
            if score > best_score:
                best, best_score = entry, score
        if best and best_score >= _FUZZY_SIMILARITY_THRESHOLD:
            logger.info("Cache hit (fuzzy match %.3f) for: %s", best_score, question)
            return best
        return None

    def _save(self) -> None:
        data = [
            {"question": e.question, "code": e.code, "explanation": e.explanation, "embedding": e.embedding}
            for e in self._entries
        ]
        self._persist_path.write_text(json.dumps(data))

    def _load(self) -> None:
        data = json.loads(self._persist_path.read_text())
        self._entries = [CacheEntry(**d) for d in data]