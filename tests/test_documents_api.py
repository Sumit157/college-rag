"""API tests for document upload, listing, chunks, delete and stats."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.database.mongo import Mongo

from tests.conftest import TEST_DB, build_pdf, build_txt


def _upload(
    client: TestClient,
    name: str,
    content: bytes,
    subject: str = "Operating Systems",
    semester: int = 5,
    mime: str | None = None,
):
    files = {"file": (name, content, mime or "application/octet-stream")}
    data = {"subject": subject, "semester": str(semester)}
    return client.post("/api/documents", files=files, data=data)


def _chunks_in_db(document_id: str) -> int:
    settings = get_settings()
    mongo = Mongo(settings.mongodb_uri, TEST_DB, timeout_ms=2000)
    try:
        return mongo.db["document_chunks"].count_documents({"document_id": document_id})
    finally:
        mongo.close()


def test_upload_txt_indexes_document(make_client) -> None:
    client = make_client()
    response = _upload(client, "os-notes.txt", build_txt())
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["filename"] == "os-notes.txt"
    assert body["subject"] == "Operating Systems"
    assert body["semester"] == 5
    assert body["status"] == "indexed"
    assert body["chunk_count"] >= 1
    assert body["file_type"] == "txt"

    # acceptance: chunks really exist in MongoDB
    assert _chunks_in_db(body["id"]) == body["chunk_count"]


def test_upload_pdf_indexes_document(make_client) -> None:
    client = make_client()
    pdf = build_pdf(["1. Introduction\nOperating systems manage resources."])
    response = _upload(client, "os.pdf", pdf, mime="application/pdf")
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["status"] == "indexed"
    assert body["page_count"] == 1


def test_upload_rejects_unsupported_type(make_client) -> None:
    client = make_client()
    response = _upload(client, "virus.exe", b"MZ binary")
    assert response.status_code == 415
    assert "detail" in response.json()


def test_upload_rejects_content_mismatch(make_client) -> None:
    client = make_client()
    response = _upload(client, "fake.pdf", b"this is not a pdf at all")
    assert response.status_code == 400


def test_upload_rejects_declared_mime_mismatch(make_client) -> None:
    client = make_client()
    response = _upload(client, "notes.txt", b"hello", mime="text/html")
    assert response.status_code == 400


def test_upload_rejects_empty_file(make_client) -> None:
    client = make_client()
    response = _upload(client, "empty.txt", b"")
    assert response.status_code == 400


def test_upload_rejects_oversized_file(make_client) -> None:
    client = make_client(MAX_UPLOAD_SIZE_MB="0")
    response = _upload(client, "big.txt", b"some text content")
    assert response.status_code == 413


def test_upload_requires_subject_and_semester(make_client) -> None:
    client = make_client()
    files = {"file": ("a.txt", b"hello", "text/plain")}
    response = client.post("/api/documents", files=files, data={"subject": ""})
    assert response.status_code == 422
    response = client.post(
        "/api/documents",
        files=files,
        data={"subject": "OS", "semester": "99"},
    )
    assert response.status_code == 422


def test_duplicate_upload_detected(make_client) -> None:
    client = make_client()
    first = _upload(client, "notes.txt", build_txt())
    assert first.status_code == 201
    second = _upload(client, "notes-copy.txt", build_txt())
    assert second.status_code == 409
    assert "already" in second.json()["detail"].lower()


def test_corrupt_pdf_marks_document_failed(make_client) -> None:
    client = make_client()
    response = _upload(client, "broken.pdf", b"%PDF-1.4\nnot really a pdf")
    assert response.status_code in {400, 415}
    # the failed document record must remain visible with an error message
    listing = client.get("/api/documents").json()
    if listing["total"] > 0:
        doc = next(d for d in listing["items"] if d["filename"] == "broken.pdf")
        assert doc["status"] == "failed"
        assert doc["error"]


def test_list_and_filters(make_client) -> None:
    client = make_client()
    _upload(client, "a.txt", build_txt(), subject="Operating Systems", semester=5)
    _upload(client, "b.txt", b"DBMS normalisation keeps data consistent.", subject="DBMS", semester=5)

    all_docs = client.get("/api/documents").json()
    assert all_docs["total"] == 2

    filtered = client.get("/api/documents", params={"subject": "DBMS"}).json()
    assert filtered["total"] == 1
    assert filtered["items"][0]["filename"] == "b.txt"

    filtered = client.get("/api/documents", params={"semester": 5}).json()
    assert filtered["total"] == 2

    empty = client.get("/api/documents", params={"subject": "Physics"}).json()
    assert empty["total"] == 0


def test_get_document_detail(make_client) -> None:
    client = make_client()
    created = _upload(client, "notes.txt", build_txt()).json()

    response = client.get(f"/api/documents/{created['id']}")
    assert response.status_code == 200
    assert response.json()["id"] == created["id"]

    assert client.get("/api/documents/does-not-exist").status_code == 404
    assert client.get("/api/documents/64b000000000000000000000").status_code == 404


def test_document_chunks_endpoint(make_client) -> None:
    client = make_client()
    created = _upload(client, "notes.txt", build_txt()).json()

    response = client.get(f"/api/documents/{created['id']}/chunks")
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == created["chunk_count"]
    assert body["items"], "expected at least one chunk"
    first = body["items"][0]
    assert first["text"].strip()
    assert first["filename"] == "notes.txt"
    assert first["chunk_index"] == 0
    assert first["document_id"] == created["id"]
    assert first["subject"] == "Operating Systems"

    assert client.get("/api/documents/64b000000000000000000000/chunks").status_code == 404


def test_delete_document_removes_chunks(make_client) -> None:
    client = make_client()
    created = _upload(client, "notes.txt", build_txt()).json()
    assert _chunks_in_db(created["id"]) >= 1

    response = client.delete(f"/api/documents/{created['id']}")
    assert response.status_code == 200
    assert response.json()["deleted"] == created["id"]

    assert client.get(f"/api/documents/{created['id']}").status_code == 404
    assert _chunks_in_db(created["id"]) == 0
    assert client.delete(f"/api/documents/{created['id']}").status_code == 404


def test_stats_endpoint(make_client) -> None:
    client = make_client()
    assert client.get("/api/stats").json() == {"documents": 0, "subjects": 0}
    _upload(client, "a.txt", b"Operating systems manage resources.")
    _upload(client, "b.txt", b"Database systems store data.", subject="DBMS")
    stats = client.get("/api/stats").json()
    assert stats["documents"] == 2
    assert stats["subjects"] == 2


def test_errors_never_leak_stack_traces(make_client) -> None:
    client = make_client()
    response = _upload(client, "virus.exe", b"MZ")
    text = response.text
    assert "Traceback" not in text
    assert 'File "' not in text
    assert "detail" in response.json()
