"""Vector store tests (require a running MongoDB; skipped otherwise)."""

from __future__ import annotations

import pytest

from app.retrieval.vector_store import (
    MongoVectorStore,
    RetrievalError,
    build_filter_expr,
    cosine_similarity,
)

from tests.conftest import TEST_DB, drop_test_db, mongo_available

pytestmark = pytest.mark.skipif(not mongo_available(), reason="MongoDB is not running")


@pytest.fixture
def db():
    from app.core.config import get_settings
    from app.database.mongo import Mongo

    drop_test_db()
    settings = get_settings()
    mongo = Mongo(settings.mongodb_uri, TEST_DB, timeout_ms=2000)
    yield mongo.db
    mongo.close()
    drop_test_db()


def _insert_chunk(db, embedding, text: str, **meta):
    record = {
        "text": text,
        "embedding": embedding,
        "page": 1,
        "section": None,
        "subject": "Operating Systems",
        "semester": 5,
        "document_id": "doc-1",
        "filename": "os.txt",
        "chunk_index": 0,
    }
    record.update(meta)
    return db["document_chunks"].insert_one(record).inserted_id


def test_cosine_similarity_basics() -> None:
    assert cosine_similarity([1.0, 0.0], [1.0, 0.0]) == pytest.approx(1.0)
    assert cosine_similarity([1.0, 0.0], [0.0, 1.0]) == pytest.approx(0.0)
    assert cosine_similarity([1.0, 0.0], [0.0, 0.0]) == 0.0
    assert cosine_similarity([1.0, 0.0], [1.0]) == 0.0
    assert cosine_similarity([1.0, 0.0], None) == 0.0


def test_build_filter_expr_skips_missing_fields() -> None:
    assert build_filter_expr({"subject": "DBMS"}) == {"subject": "DBMS"}
    assert build_filter_expr({"semester": 5, "document_id": None}) == {"semester": 5}
    assert build_filter_expr({}) == {}


def test_local_search_ranks_similar_chunks_first(db) -> None:
    _insert_chunk(db, [1.0, 0.0, 0.0], "match")
    _insert_chunk(db, [0.0, 1.0, 0.0], "other", filename="other.txt")
    _insert_chunk(db, None, "unembedded")

    store = MongoVectorStore(db, mode="local")
    results = store.similarity_search([1.0, 0.0, 0.0], 5, {})

    assert [c.text for c in results] == ["match"]
    assert results[0].score == pytest.approx(1.0)
    assert results[0].filename == "os.txt"


def test_local_search_respects_top_k_and_orders_by_score(db) -> None:
    _insert_chunk(db, [1.0, 0.5, 0.0], "best")
    _insert_chunk(db, [1.0, 0.0, 0.0], "mid")
    _insert_chunk(db, [0.5, 0.5, 0.5], "worst")

    store = MongoVectorStore(db, mode="local")
    results = store.similarity_search([1.0, 0.0, 0.0], 2, {})

    assert len(results) == 2
    assert results[0].text == "mid"
    assert results[0].score >= results[1].score


def test_local_search_applies_metadata_filters(db) -> None:
    _insert_chunk(db, [1.0, 0.0], "os-chunk")
    _insert_chunk(
        db,
        [1.0, 0.0],
        "dbms-chunk",
        subject="DBMS",
        semester=6,
        document_id="doc-2",
        filename="dbms.txt",
    )

    store = MongoVectorStore(db, mode="local")

    by_subject = store.similarity_search([1.0, 0.0], 5, {"subject": "DBMS"})
    assert [c.text for c in by_subject] == ["dbms-chunk"]

    by_semester = store.similarity_search([1.0, 0.0], 5, {"semester": 6})
    assert [c.text for c in by_semester] == ["dbms-chunk"]

    by_document = store.similarity_search([1.0, 0.0], 5, {"document_id": "doc-2"})
    assert [c.text for c in by_document] == ["dbms-chunk"]

    no_match = store.similarity_search([1.0, 0.0], 5, {"subject": "Physics"})
    assert no_match == []


def test_auto_mode_returns_results_via_fallback_or_vector(db) -> None:
    _insert_chunk(db, [1.0, 0.0], "match")

    store = MongoVectorStore(db, mode="auto")
    results = store.similarity_search([1.0, 0.0], 3, {})

    assert [c.text for c in results] == ["match"]
    # either the server supports $vectorSearch or we fell back to local scoring
    assert store.mode in {"auto", "vector", "local"}


def test_strict_vector_mode_reports_failure_or_returns(db) -> None:
    _insert_chunk(db, [1.0, 0.0], "match")
    store = MongoVectorStore(db, mode="vector")
    try:
        results = store.similarity_search([1.0, 0.0], 3, {})
    except RetrievalError as exc:
        # standalone MongoDB: strict mode fails loudly instead of degrading
        assert exc.message
    else:
        # Atlas-capable server: strict mode returns results
        assert [c.text for c in results] == ["match"]


def test_ensure_index_never_raises(db) -> None:
    MongoVectorStore(db, mode="auto").ensure_index()
