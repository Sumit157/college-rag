"""Unit tests for the local embedding provider (MockTransport, no Ollama)."""

from __future__ import annotations

import json

import httpx
import pytest

from app.embeddings import EmbeddingError, LocalEmbeddingProvider


def _make(handler, **kwargs) -> LocalEmbeddingProvider:
    return LocalEmbeddingProvider(
        base_url="http://ollama.test",
        model="test-model",
        transport=httpx.MockTransport(handler),
        **kwargs,
    )


def test_embed_returns_vectors_in_order() -> None:
    seen: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        seen["path"] = request.url.path
        seen["model"] = body["model"]
        inputs = body["input"]
        return httpx.Response(
            200,
            json={"embeddings": [[float(i)] * 4 for i in range(len(inputs))]},
        )

    provider = _make(handler)
    vectors = provider.embed(["alpha", "beta", "gamma"])

    assert vectors == [[0.0] * 4, [1.0] * 4, [2.0] * 4]
    assert seen["path"] == "/api/embed"
    assert seen["model"] == "test-model"
    assert provider.model == "test-model"


def test_embed_query_returns_single_vector() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        assert body["input"] == ["paging"]
        return httpx.Response(200, json={"embeddings": [[0.5, 0.25]]})

    provider = _make(handler)
    assert provider.embed_query("paging") == [0.5, 0.25]


def test_batching_splits_large_requests() -> None:
    calls: list[int] = []

    def handler(request: httpx.Request) -> httpx.Response:
        inputs = json.loads(request.content)["input"]
        calls.append(len(inputs))
        return httpx.Response(
            200, json={"embeddings": [[1.0] for _ in inputs]}
        )

    provider = _make(handler, batch_size=2)
    vectors = provider.embed(["a", "b", "c", "d", "e"])

    assert calls == [2, 2, 1]
    assert len(vectors) == 5


def test_server_unreachable_raises_embedding_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection refused")

    provider = _make(handler)
    with pytest.raises(EmbeddingError) as excinfo:
        provider.embed(["text"])
    assert "unavailable" in excinfo.value.message.lower()
    assert excinfo.value.status_code == 503


def test_http_error_raises_embedding_error() -> None:
    provider = _make(lambda request: httpx.Response(500, json={"error": "boom"}))
    with pytest.raises(EmbeddingError):
        provider.embed(["text"])


def test_malformed_response_raises_embedding_error() -> None:
    provider = _make(lambda request: httpx.Response(200, json={"embeddings": []}))
    with pytest.raises(EmbeddingError):
        provider.embed(["text"])


def test_falls_back_to_legacy_endpoint() -> None:
    paths: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        paths.append(request.url.path)
        if request.url.path == "/api/embed":
            return httpx.Response(404)
        return httpx.Response(200, json={"embedding": [1.0, 2.0]})

    provider = _make(handler)
    first = provider.embed(["a"])
    second = provider.embed(["b"])

    assert first == [[1.0, 2.0]]
    assert second == [[1.0, 2.0]]
    # after the first 404, only legacy calls are made
    assert paths == ["/api/embed", "/api/embeddings", "/api/embeddings"]
