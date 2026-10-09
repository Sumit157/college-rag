"""Retriever: question → query embedding → vector search → evidence."""

from __future__ import annotations

from typing import Any

from app.core.config import get_settings
from app.embeddings.errors import EmbeddingError
from app.embeddings.provider import EmbeddingProvider
from app.models.evidence import Evidence
from app.retrieval.evidence import build_evidence
from app.retrieval.vector_store import VectorStore


class Retriever:
    def __init__(
        self,
        embeddings: EmbeddingProvider,
        store: VectorStore,
        default_top_k: int | None = None,
    ) -> None:
        settings = get_settings()
        self._embeddings = embeddings
        self._store = store
        self._default_top_k = default_top_k or settings.retrieval_top_k

    def retrieve(
        self,
        *,
        query: str,
        subject: str | None = None,
        semester: int | None = None,
        document_id: str | None = None,
        top_k: int | None = None,
    ) -> list[Evidence]:
        k = top_k or self._default_top_k
        vector = self._embeddings.embed_query(query)
        if not vector:
            raise EmbeddingError("The embedding model returned no result. Please try again.")
        filters: dict[str, Any] = {
            key: value
            for key, value in {
                "subject": subject,
                "semester": semester,
                "document_id": document_id,
            }.items()
            if value is not None
        }
        results = self._store.similarity_search(vector, k, filters)
        return build_evidence(results)
