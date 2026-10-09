"""Embedding errors with user-safe messages and HTTP status codes."""

from __future__ import annotations


class EmbeddingError(Exception):
    status_code = 503

    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(message)
