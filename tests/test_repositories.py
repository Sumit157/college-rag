"""Repository tests (require a running MongoDB; skipped otherwise)."""

from datetime import datetime, timezone

import pytest

from app.database.repositories import ChunkRepository, DocumentRepository, to_object_id

from tests.conftest import TEST_DB, drop_test_db, mongo_available

pytestmark = pytest.mark.skipif(not mongo_available(), reason="MongoDB is not running")


@pytest.fixture
def db():
    from app.database.mongo import Mongo
    from app.core.config import get_settings

    drop_test_db()
    settings = get_settings()
    mongo = Mongo(settings.mongodb_uri, TEST_DB, timeout_ms=2000)
    yield mongo.db
    mongo.close()
    drop_test_db()


def _doc(**overrides) -> dict:
    record = {
        "filename": "OS Notes.pdf",
        "file_hash": "hash123",
        "file_type": "pdf",
        "subject": "Operating Systems",
        "semester": 5,
        "status": "processing",
        "size_bytes": 1000,
        "chunk_count": 0,
        "page_count": None,
        "error": None,
        "created_at": datetime.now(timezone.utc),
    }
    record.update(overrides)
    return record


def test_create_and_get_document(db) -> None:
    repo = DocumentRepository(db)
    created = repo.create(_doc())
    fetched = repo.get(str(created["_id"]))
    assert fetched is not None
    assert fetched["filename"] == "OS Notes.pdf"
    assert fetched["subject"] == "Operating Systems"
    assert fetched["semester"] == 5


def test_get_invalid_id_returns_none(db) -> None:
    repo = DocumentRepository(db)
    assert repo.get("not-an-objectid") is None
    assert to_object_id("nope") is None


def test_get_by_hash_detects_duplicates(db) -> None:
    repo = DocumentRepository(db)
    repo.create(_doc())
    assert repo.get_by_hash("hash123") is not None
    assert repo.get_by_hash("other") is None


def test_list_filters_by_subject_and_semester(db) -> None:
    repo = DocumentRepository(db)
    repo.create(_doc(file_hash="a", subject="Operating Systems", semester=5))
    repo.create(_doc(file_hash="b", subject="DBMS", semester=5))
    repo.create(_doc(file_hash="c", subject="DBMS", semester=6))

    assert len(repo.list()) == 3
    assert len(repo.list(subject="DBMS")) == 2
    assert len(repo.list(semester=6)) == 1
    assert len(repo.list(subject="DBMS", semester=5)) == 1


def test_list_sorted_by_created_at_desc(db) -> None:
    repo = DocumentRepository(db)
    first = repo.create(_doc(file_hash="a", created_at=datetime(2026, 1, 1, tzinfo=timezone.utc)))
    second = repo.create(_doc(file_hash="b", created_at=datetime(2026, 6, 1, tzinfo=timezone.utc)))
    items = repo.list()
    assert [str(i["_id"]) for i in items] == [str(second["_id"]), str(first["_id"])]


def test_mark_indexed_and_failed(db) -> None:
    repo = DocumentRepository(db)
    created = repo.create(_doc())
    doc_id = str(created["_id"])

    indexed = repo.mark_indexed(doc_id, chunk_count=12, page_count=3)
    assert indexed["status"] == "indexed"
    assert indexed["chunk_count"] == 12
    assert indexed["page_count"] == 3

    failed = repo.mark_failed(doc_id, "broken file")
    assert failed["status"] == "failed"
    assert failed["error"] == "broken file"


def test_delete_document_removes_chunks(db) -> None:
    docs = DocumentRepository(db)
    chunks = ChunkRepository(db)
    created = docs.create(_doc())
    doc_id = str(created["_id"])
    chunks.insert_many(
        [
            {
                "document_id": doc_id,
                "filename": "OS Notes.pdf",
                "text": f"chunk {i}",
                "page": 1,
                "section": "Paging",
                "subject": "Operating Systems",
                "semester": 5,
                "chunk_index": i,
                "embedding": None,
            }
            for i in range(3)
        ]
    )
    assert chunks.count_by_document(doc_id) == 3

    assert docs.delete(doc_id) is True
    assert docs.get(doc_id) is None
    assert chunks.count_by_document(doc_id) == 0


def test_chunk_listing_pagination(db) -> None:
    docs = DocumentRepository(db)
    chunks = ChunkRepository(db)
    created = docs.create(_doc())
    doc_id = str(created["_id"])
    chunks.insert_many(
        [
            {
                "document_id": doc_id,
                "filename": "OS Notes.pdf",
                "text": f"chunk {i}",
                "page": None,
                "section": None,
                "subject": "Operating Systems",
                "semester": 5,
                "chunk_index": i,
                "embedding": None,
            }
            for i in range(10)
        ]
    )
    items, total = chunks.list_by_document(doc_id, limit=4, offset=4)
    assert total == 10
    assert [c["chunk_index"] for c in items] == [4, 5, 6, 7]


def test_stats(db) -> None:
    repo = DocumentRepository(db)
    assert repo.stats() == {"documents": 0, "subjects": 0}
    repo.create(_doc(subject="Operating Systems"))
    repo.create(_doc(file_hash="x", subject="Operating Systems"))
    repo.create(_doc(file_hash="y", subject="DBMS"))
    stats = repo.stats()
    assert stats["documents"] == 3
    assert stats["subjects"] == 2
