"""Backfill embeddings for chunks ingested before embedding was wired up."""

from __future__ import annotations

import logging

from pymongo import UpdateOne
from pymongo.database import Database

from app.embeddings.errors import EmbeddingError
from app.embeddings.provider import EmbeddingProvider

logger = logging.getLogger(__name__)

MISSING = {"$or": [{"embedding": None}, {"embedding": {"$exists": False}}]}
BATCH_SIZE = 64


def backfill_embeddings(
    db: Database,
    provider: EmbeddingProvider,
    batch_size: int = BATCH_SIZE,
) -> int:
    """Embed every chunk that is missing a vector. Returns the update count."""
    col = db["document_chunks"]
    texts: list[tuple[object, str]] = []
    for doc in col.find(MISSING, {"text": 1}):
        text = doc.get("text")
        if isinstance(text, str) and text:
            texts.append((doc["_id"], text))

    if not texts:
        return 0

    logger.info("Backfilling embeddings for %d chunks", len(texts))
    updated = 0
    for start in range(0, len(texts), batch_size):
        batch = texts[start : start + batch_size]
        vectors = provider.embed([text for _, text in batch])
        if len(vectors) != len(batch):
            raise EmbeddingError("The embedding model returned an unexpected response.")
        operations = [
            UpdateOne({"_id": chunk_id}, {"$set": {"embedding": vector}})
            for (chunk_id, _), vector in zip(batch, vectors)
        ]
        result = col.bulk_write(operations)
        updated += result.modified_count
    return updated
