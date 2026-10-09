"""Retriever unit tests (fake embedding provider, stub vector store)."""

from __future__ import annotations

import pytest

from app.embeddings.errors import EmbeddingError
from app.retrieval.retriever import Retriever
from app.retrieval.vector_store import ScoredChunk

from tests.conftest import FakeEmbeddingProvider


class StubStore:
    def __init__(self, results: list[ScoredChunk]) -> None:
        self.results = results
        self.calls: list[tuple[list[float], int, dict]] = []

    def similarity_search(self, vector, top_k, filters):
        self.calls.append((vector, top_k, filters))
        return self.results


class FailingEmbeddings:
    model = "broken"

    def embed(self, texts):
        return [[] for _ in texts]

    def embed_query(self, text):
        return []


def _chunk(text: str, score: float, **overrides) -> ScoredChunk:
    fields = {
        "chunk_id": "chunk-1",
        "document_id": "doc-1",
        "filename": "os.txt",
        "text": text,
        "page": 4,
        "section": "Paging",
        "subject": "Operating Systems",
        "semester": 5,
        "score": score,
    }
    fields.update(overrides)
    return ScoredChunk(**fields)


def test_retrieve_builds_numbered_evidence() -> None:
    store = StubStore(
        [
            _chunk("first", 0.9),
            _chunk("second", 0.8, chunk_id="chunk-2", page=None, section=None),
        ]
    )
    retriever = Retriever(FakeEmbeddingProvider(), store, default_top_k=5)

    evidence = retriever.retrieve(query="paging")

    assert [e.id for e in evidence] == ["evidence-1", "evidence-2"]
    first, second = evidence
    assert first.document_id == "doc-1"
    assert first.filename == "os.txt"
    assert first.page == 4
    assert first.section == "Paging"
    assert first.chunk_id == "chunk-1"
    assert first.text == "first"
    assert first.relevance == pytest.approx(0.9)
    assert second.page is None
    assert second.section is None


def test_retrieve_passes_top_k_and_empty_filters() -> None:
    store = StubStore([])
    retriever = Retriever(FakeEmbeddingProvider(), store, default_top_k=5)

    retriever.retrieve(query="q", top_k=3)

    _, top_k, filters = store.calls[0]
    assert top_k == 3
    assert filters == {}


def test_retrieve_uses_default_top_k_from_settings() -> None:
    store = StubStore([])
    retriever = Retriever(FakeEmbeddingProvider(), store)

    retriever.retrieve(query="q")

    _, top_k, _ = store.calls[0]
    assert top_k >= 1


def test_retrieve_passes_metadata_filters() -> None:
    store = StubStore([])
    retriever = Retriever(FakeEmbeddingProvider(), store)

    retriever.retrieve(query="q", subject="DBMS", semester=5, document_id="doc-9")

    _, _, filters = store.calls[0]
    assert filters == {"subject": "DBMS", "semester": 5, "document_id": "doc-9"}


def test_retrieve_omits_none_filters() -> None:
    store = StubStore([])
    retriever = Retriever(FakeEmbeddingProvider(), store)

    retriever.retrieve(query="q", subject="DBMS", semester=None, document_id=None)

    _, _, filters = store.calls[0]
    assert filters == {"subject": "DBMS"}


def test_relevance_is_clamped_to_unit_range() -> None:
    store = StubStore(
        [
            _chunk("too-high", 1.7),
            _chunk("negative", -0.3),
        ]
    )
    retriever = Retriever(FakeEmbeddingProvider(), store)

    evidence = retriever.retrieve(query="q")

    assert evidence[0].relevance == 1.0
    assert evidence[1].relevance == 0.0


def test_empty_embedding_raises_embedding_error() -> None:
    store = StubStore([])
    retriever = Retriever(FailingEmbeddings(), store)

    with pytest.raises(EmbeddingError):
        retriever.retrieve(query="q")
