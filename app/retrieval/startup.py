"""Retrieval startup work: vector index and embedding backfill.

Everything here is best-effort — retrieval degrades gracefully (local scoring,
missing embeddings) instead of blocking application startup.
"""

from __future__ import annotations

import logging

from pymongo.database import Database

from app.embeddings.backfill import backfill_embeddings
from app.embeddings.provider import get_embedding_provider
from app.retrieval.vector_store import get_vector_store

logger = logging.getLogger(__name__)


def ensure_retrieval_ready(db: Database) -> None:
    try:
        get_vector_store().ensure_index()
    except Exception:
        logger.warning("Could not ensure the vector search index", exc_info=True)
    try:
        backfill_embeddings(db, get_embedding_provider())
    except Exception:
        logger.warning("Could not backfill missing embeddings", exc_info=True)
