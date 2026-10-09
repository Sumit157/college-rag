"""Embedding providers: interface and local Ollama implementation."""

from app.embeddings.errors import EmbeddingError
from app.embeddings.provider import EmbeddingProvider, LocalEmbeddingProvider, get_embedding_provider

__all__ = [
    "EmbeddingError",
    "EmbeddingProvider",
    "LocalEmbeddingProvider",
    "get_embedding_provider",
]
