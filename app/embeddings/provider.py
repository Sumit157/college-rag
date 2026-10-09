"""Embedding provider interface and local Ollama implementation.

The interface is intentionally tiny so a hosted or different local embedding
runtime can replace LocalEmbeddingProvider without touching callers.
"""

from __future__ import annotations

import math
import re
from typing import Protocol

import httpx

from app.core.config import get_settings
from app.embeddings.errors import EmbeddingError

DEFAULT_BATCH_SIZE = 64

_UNAVAILABLE = "The embedding model is unavailable. Please try again in a moment."
BAD_RESPONSE = "The embedding model returned an unexpected response. Please try again."


class EmbeddingProvider(Protocol):
    @property
    def model(self) -> str: ...

    def embed(self, texts: list[str]) -> list[list[float]]: ...

    def embed_query(self, text: str) -> list[float]: ...


class LocalEmbeddingProvider:
    """Talks to a local Ollama server (/api/embed, with /api/embeddings fallback)."""

    def __init__(
        self,
        base_url: str | None = None,
        model: str | None = None,
        timeout_s: float | None = None,
        batch_size: int = DEFAULT_BATCH_SIZE,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        settings = get_settings()
        self._base_url = (base_url or settings.ollama_base_url).rstrip("/")
        self._model = model or settings.embedding_model
        self._timeout_s = timeout_s or settings.ollama_timeout_s
        self._batch_size = max(1, batch_size)
        self._transport = transport
        self._use_legacy_endpoint = False

    @property
    def model(self) -> str:
        return self._model

    def embed(self, texts: list[str]) -> list[list[float]]:
        vectors: list[list[float]] = []
        for start in range(0, len(texts), self._batch_size):
            vectors.extend(self._embed_batch(texts[start : start + self._batch_size]))
        return vectors

    def embed_query(self, text: str) -> list[float]:
        return self.embed([text])[0]

    def _embed_batch(self, batch: list[str]) -> list[list[float]]:
        with httpx.Client(timeout=self._timeout_s, transport=self._transport) as client:
            if not self._use_legacy_endpoint:
                vectors = self._embed_via_api(client, batch)
                if vectors is not None:
                    return vectors
            return self._embed_via_legacy_api(client, batch)

    def _embed_via_api(
        self, client: httpx.Client, batch: list[str]
    ) -> list[list[float]] | None:
        """POST /api/embed (batched). Returns None to trigger legacy fallback."""
        try:
            response = client.post(
                f"{self._base_url}/api/embed",
                json={"model": self._model, "input": batch},
            )
        except httpx.HTTPError as exc:
            raise EmbeddingError(_UNAVAILABLE) from exc
        if response.status_code == 404:
            self._use_legacy_endpoint = True
            return None
        if response.status_code >= 400:
            raise EmbeddingError(_UNAVAILABLE)
        try:
            embeddings = response.json().get("embeddings")
        except ValueError as exc:
            raise EmbeddingError(BAD_RESPONSE) from exc
        if not isinstance(embeddings, list) or len(embeddings) != len(batch):
            raise EmbeddingError(BAD_RESPONSE)
        if any(not isinstance(vector, list) or not vector for vector in embeddings):
            raise EmbeddingError(BAD_RESPONSE)
        return embeddings

    def _embed_via_legacy_api(
        self, client: httpx.Client, batch: list[str]
    ) -> list[list[float]]:
        """POST /api/embeddings (one prompt per request, pre-0.1.33 Ollama)."""
        vectors: list[list[float]] = []
        for text in batch:
            try:
                response = client.post(
                    f"{self._base_url}/api/embeddings",
                    json={"model": self._model, "prompt": text},
                )
            except httpx.HTTPError as exc:
                raise EmbeddingError(_UNAVAILABLE) from exc
            if response.status_code >= 400:
                raise EmbeddingError(_UNAVAILABLE)
            try:
                vector = response.json().get("embedding")
            except ValueError as exc:
                raise EmbeddingError(BAD_RESPONSE) from exc
            if not isinstance(vector, list) or not vector:
                raise EmbeddingError(BAD_RESPONSE)
            vectors.append(vector)
        return vectors


_provider: LocalEmbeddingProvider | None = None


def get_embedding_provider() -> LocalEmbeddingProvider:
    """Application-wide embedding provider (lazy singleton)."""
    global _provider
    if _provider is None:
        _provider = LocalEmbeddingProvider()
    return _provider
