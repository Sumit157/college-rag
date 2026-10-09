"""API tests for semantic search (hermetic fake embeddings, live MongoDB)."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.database.mongo import Mongo
from app.embeddings.errors import EmbeddingError

from tests.conftest import TEST_DB, FakeEmbeddingProvider, build_txt

# shares "manage"/"resources" with build_txt() so unfiltered searches can match both
DBMS_TXT = b"Normalisation removes redundancy. Database schemas manage data resources."


@pytest.fixture(autouse=True)
def fake_embeddings(monkeypatch) -> None:
    """One shared fake provider so uploads and queries use the same vector space."""
    from app.api.routes import documents as documents_route
    from app.api.routes import search as search_route

    fake = FakeEmbeddingProvider()
    monkeypatch.setattr(documents_route, "get_embedding_provider", lambda: fake)
    monkeypatch.setattr(search_route, "get_embedding_provider", lambda: fake)


def _upload(
    client: TestClient,
    name: str,
    content: bytes,
    subject: str = "Operating Systems",
    semester: int = 5,
):
    files = {"file": (name, content, "text/plain")}
    data = {"subject": subject, "semester": str(semester)}
    response = client.post("/api/documents", files=files, data=data)
    assert response.status_code == 201, response.text
    return response.json()


def _chunks_from_db():
    settings = get_settings()
    mongo = Mongo(settings.mongodb_uri, TEST_DB, timeout_ms=2000)
    try:
        return list(mongo.db["document_chunks"].find({}, {"embedding": 1}))
    finally:
        mongo.close()


def test_ingestion_stores_embeddings_with_chunks(make_client) -> None:
    client = make_client()
    created = _upload(client, "os.txt", build_txt())

    chunks = _chunks_from_db()
    assert len(chunks) == created["chunk_count"]
    for chunk in chunks:
        vector = chunk.get("embedding")
        assert isinstance(vector, list) and len(vector) == 32


def test_search_returns_evidence_objects(make_client) -> None:
    client = make_client()
    _upload(client, "os.txt", build_txt())

    response = client.post("/api/search", json={"query": "paging divides physical memory"})

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["query"] == "paging divides physical memory"
    assert body["count"] == len(body["evidence"])
    assert body["evidence"], "expected at least one evidence object"

    evidence = body["evidence"][0]
    assert set(evidence) == {
        "id",
        "document_id",
        "filename",
        "page",
        "section",
        "chunk_id",
        "text",
        "relevance",
    }
    assert evidence["id"] == "evidence-1"
    assert evidence["filename"] == "os.txt"
    assert evidence["text"].strip()
    assert 0.0 <= evidence["relevance"] <= 1.0


def test_search_ranks_matching_document_first(make_client) -> None:
    client = make_client()
    _upload(client, "os.txt", build_txt())
    _upload(client, "dbms.txt", DBMS_TXT, subject="DBMS", semester=6)

    body = client.post(
        "/api/search", json={"query": "paging divides physical memory"}
    ).json()

    assert body["evidence"]
    assert body["evidence"][0]["filename"] == "os.txt"
    assert [e["id"] for e in body["evidence"]] == [
        f"evidence-{i}" for i in range(1, len(body["evidence"]) + 1)
    ]


def test_search_filters_by_subject(make_client) -> None:
    client = make_client()
    _upload(client, "os.txt", build_txt())
    _upload(client, "dbms.txt", DBMS_TXT, subject="DBMS", semester=6)

    # without the filter, the query matches both documents
    unfiltered = client.post("/api/search", json={"query": "manage resources"}).json()
    assert {e["filename"] for e in unfiltered["evidence"]} == {"os.txt", "dbms.txt"}

    # with subject=DBMS, only the DBMS document survives the filter
    body = client.post(
        "/api/search",
        json={"query": "manage resources", "subject": "DBMS"},
    ).json()

    assert body["count"] >= 1
    assert all(e["filename"] == "dbms.txt" for e in body["evidence"])


def test_search_filters_by_semester(make_client) -> None:
    client = make_client()
    _upload(client, "os.txt", build_txt(), semester=5)
    _upload(client, "dbms.txt", DBMS_TXT, subject="DBMS", semester=6)

    body = client.post(
        "/api/search", json={"query": "manage resources", "semester": 6}
    ).json()

    assert body["count"] >= 1
    assert all(e["filename"] == "dbms.txt" for e in body["evidence"])


def test_search_filters_by_document_id(make_client) -> None:
    client = make_client()
    first = _upload(client, "os.txt", build_txt())
    _upload(client, "dbms.txt", DBMS_TXT, subject="DBMS", semester=6)

    body = client.post(
        "/api/search",
        json={"query": "manage resources", "document_id": first["id"]},
    ).json()

    assert body["count"] >= 1
    assert all(e["document_id"] == first["id"] for e in body["evidence"])
    assert all(e["filename"] == "os.txt" for e in body["evidence"])


def test_search_empty_library_returns_no_evidence(make_client) -> None:
    client = make_client()
    body = client.post("/api/search", json={"query": "anything at all"}).json()
    assert body == {"query": "anything at all", "evidence": [], "count": 0}


def test_search_honours_top_k(make_client) -> None:
    client = make_client()
    _upload(client, "os.txt", build_txt())

    body = client.post(
        "/api/search", json={"query": "paging divides memory", "top_k": 1}
    ).json()

    assert body["count"] <= 1


def test_search_rejects_blank_query(make_client) -> None:
    client = make_client()
    assert client.post("/api/search", json={"query": ""}).status_code == 422
    assert client.post("/api/search", json={"query": "   "}).status_code == 422


def test_search_rejects_invalid_top_k(make_client) -> None:
    client = make_client()
    assert (
        client.post("/api/search", json={"query": "x", "top_k": 0}).status_code == 422
    )
    assert (
        client.post("/api/search", json={"query": "x", "top_k": 51}).status_code == 422
    )


def test_search_embedding_failure_returns_user_safe_503(
    make_client, monkeypatch
) -> None:
    from app.api.routes import search as search_route

    class BrokenEmbeddings:
        model = "broken"

        def embed(self, texts):
            raise EmbeddingError("The embedding model is unavailable.")

        def embed_query(self, text):
            raise EmbeddingError("The embedding model is unavailable.")

    monkeypatch.setattr(
        search_route, "get_embedding_provider", lambda: BrokenEmbeddings()
    )

    client = make_client()
    response = client.post("/api/search", json={"query": "paging"})

    assert response.status_code == 503
    assert "unavailable" in response.json()["detail"].lower()
    assert "Traceback" not in response.text
