"""Vector search over document chunks in MongoDB.

Two execution modes:

- "vector": MongoDB Atlas `$vectorSearch` with a vector search index. Works on
  Atlas and AtlasCLI local deployments only.
- "local": cosine similarity computed in-process over metadata-filtered chunks.
  Works on any MongoDB deployment (standalone Community included).

"auto" (default) prefers $vectorSearch and permanently falls back to local
scoring for the current store instance when the server rejects the stage.
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass
from typing import Any, Protocol

from pymongo.database import Database

from app.core.config import get_settings
from app.database.mongo import get_mongo

logger = logging.getLogger(__name__)

FILTER_FIELDS = ("subject", "semester", "document_id")

# Server capability probe: set to False once the deployment rejects the
# $vectorSearch stage (standalone Community), True once it accepts it.
# None means "not probed yet in this process".
_VECTOR_STAGE_OK: bool | None = None


class RetrievalError(Exception):
    """Retrieval backend failure with a user-safe message."""

    def __init__(self, message: str = "Search is temporarily unavailable.") -> None:
        self.message = message
        super().__init__(message)


@dataclass
class ScoredChunk:
    chunk_id: str
    document_id: str
    filename: str
    text: str
    page: int | None
    section: str | None
    subject: str | None
    semester: int | None
    score: float


class VectorStore(Protocol):
    def similarity_search(
        self,
        vector: list[float],
        top_k: int,
        filters: dict[str, Any],
    ) -> list[ScoredChunk]: ...


def build_filter_expr(filters: dict[str, Any]) -> dict[str, Any]:
    return {
        key: filters[key]
        for key in FILTER_FIELDS
        if filters.get(key) is not None
    }


def cosine_similarity(a: list[float], b: list[float] | None) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = 0.0
    norm_a = 0.0
    norm_b = 0.0
    for x, y in zip(a, b):
        dot += x * y
        norm_a += x * x
        norm_b += y * y
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return dot / math.sqrt(norm_a * norm_b)


def _mark_vector_stage(unavailable: bool) -> None:
    global _VECTOR_STAGE_OK
    _VECTOR_STAGE_OK = not unavailable


def _to_scored(doc: dict[str, Any], score: float) -> ScoredChunk:
    return ScoredChunk(
        chunk_id=str(doc["_id"]),
        document_id=str(doc.get("document_id", "")),
        filename=str(doc.get("filename", "")),
        text=str(doc.get("text", "")),
        page=doc.get("page"),
        section=doc.get("section"),
        subject=doc.get("subject"),
        semester=doc.get("semester"),
        score=score,
    )


class MongoVectorStore:
    INDEX_NAME = "chunk_vector_index"

    _PROJECT = {
        "text": 1,
        "page": 1,
        "section": 1,
        "subject": 1,
        "semester": 1,
        "document_id": 1,
        "filename": 1,
        "chunk_index": 1,
        "score": {"$meta": "vectorSearchScore"},
    }

    def __init__(self, db: Database, mode: str | None = None) -> None:
        settings = get_settings()
        configured = (mode or settings.vector_search_mode or "auto").lower()
        if configured not in ("auto", "vector", "local"):
            logger.warning("Unknown VECTOR_SEARCH_MODE %r; using 'auto'", configured)
            configured = "auto"
        self._db = db
        self._col = db["document_chunks"]
        self._mode = configured
        self._fell_back = False

    @property
    def mode(self) -> str:
        if self._mode == "auto" and (self._fell_back or _VECTOR_STAGE_OK is False):
            return "local"
        return self._mode

    def ensure_index(self) -> None:
        """Best-effort creation of the Atlas vector search index."""
        if self._mode == "local" or _VECTOR_STAGE_OK is False:
            return
        settings = get_settings()
        try:
            self._db.command(
                {
                    "createSearchIndexes": "document_chunks",
                    "indexes": [
                        {
                            "name": self.INDEX_NAME,
                            "type": "vectorSearch",
                            "definition": {
                                "fields": [
                                    {
                                        "type": "vector",
                                        "path": "embedding",
                                        "numDimensions": settings.embedding_dims,
                                        "similarity": "cosine",
                                    }
                                ]
                            },
                        }
                    ],
                }
            )
            logger.info("Vector search index '%s' is in place", self.INDEX_NAME)
        except Exception as exc:
            _mark_vector_stage(unavailable=True)
            logger.warning(
                "Vector search index could not be created (%s). "
                "Semantic search will use local cosine scoring.",
                str(exc).split("\n")[0][:200],
            )

    def similarity_search(
        self,
        vector: list[float],
        top_k: int,
        filters: dict[str, Any],
    ) -> list[ScoredChunk]:
        if self.mode == "local":
            return self._local_search(vector, top_k, filters)
        try:
            results = self._vector_search(vector, top_k, filters)
        except Exception as exc:
            if self._mode == "vector":
                logger.error("$vectorSearch failed: %s", exc)
                raise RetrievalError() from exc
            _mark_vector_stage(unavailable=True)
            logger.warning(
                "$vectorSearch unavailable (%s); using local cosine scoring.",
                str(exc).split("\n")[0][:200],
            )
            return self._local_search(vector, top_k, filters)
        _mark_vector_stage(unavailable=False)
        return results

    def _vector_search(
        self,
        vector: list[float],
        top_k: int,
        filters: dict[str, Any],
    ) -> list[ScoredChunk]:
        expr = build_filter_expr(filters)
        vector_stage: dict[str, Any] = {
            "index": self.INDEX_NAME,
            "path": "embedding",
            "queryVector": vector,
            "numCandidates": max(top_k * 20, 200),
            "limit": top_k,
        }
        if expr:
            vector_stage["filter"] = {
                "$and": [{key: {"$eq": value}} for key, value in expr.items()]
            }
        pipeline: list[dict[str, Any]] = [
            {"$vectorSearch": vector_stage},
            {"$project": self._PROJECT},
        ]
        return [
            _to_scored(doc, float(doc.get("score", 0.0)))
            for doc in self._col.aggregate(pipeline)
        ]

    def _local_search(
        self,
        vector: list[float],
        top_k: int,
        filters: dict[str, Any],
    ) -> list[ScoredChunk]:
        query = build_filter_expr(filters)
        projection = {
            "embedding": 1,
            "text": 1,
            "page": 1,
            "section": 1,
            "subject": 1,
            "semester": 1,
            "document_id": 1,
            "filename": 1,
            "chunk_index": 1,
        }
        scored: list[ScoredChunk] = []
        for doc in self._col.find(query, projection):
            score = cosine_similarity(vector, doc.get("embedding"))
            if score > 0.0:
                scored.append(_to_scored(doc, score))
        scored.sort(key=lambda chunk: chunk.score, reverse=True)
        return scored[:top_k]


_store: MongoVectorStore | None = None
_store_db: Database | None = None


def get_vector_store() -> MongoVectorStore:
    """Current vector store, rebuilt whenever the Mongo database changes."""
    global _store, _store_db
    db = get_mongo().db
    if _store is None or _store_db is not db:
        _store = MongoVectorStore(db)
        _store_db = db
    return _store
