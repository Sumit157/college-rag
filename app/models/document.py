"""Document and chunk API schemas."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum

from pydantic import BaseModel, Field


class DocumentStatus(str, Enum):
    uploaded = "uploaded"
    processing = "processing"
    indexed = "indexed"
    failed = "failed"


class DocumentOut(BaseModel):
    id: str
    filename: str
    file_type: str
    file_hash: str
    subject: str
    semester: int
    status: str
    error: str | None = None
    chunk_count: int = 0
    page_count: int | None = None
    size_bytes: int
    created_at: datetime


class ChunkOut(BaseModel):
    id: str
    document_id: str
    filename: str
    text: str
    page: int | None = None
    section: str | None = None
    subject: str
    semester: int
    chunk_index: int


class ChunkListResponse(BaseModel):
    items: list[ChunkOut]
    total: int


class StatsResponse(BaseModel):
    documents: int
    subjects: int


class DeleteResponse(BaseModel):
    deleted: str


class DocumentListResponse(BaseModel):
    items: list[DocumentOut]
    total: int


def document_to_out(doc: dict) -> DocumentOut:
    return DocumentOut(
        id=str(doc["_id"]),
        filename=doc.get("filename", ""),
        file_type=doc.get("file_type", ""),
        file_hash=doc.get("file_hash", ""),
        subject=doc.get("subject", ""),
        semester=int(doc.get("semester", 0)),
        status=doc.get("status", "uploaded"),
        error=doc.get("error"),
        chunk_count=int(doc.get("chunk_count", 0)),
        page_count=doc.get("page_count"),
        size_bytes=int(doc.get("size_bytes", 0)),
        created_at=doc.get("created_at") or datetime.now(timezone.utc),
    )


def chunk_to_out(chunk: dict) -> ChunkOut:
    return ChunkOut(
        id=str(chunk["_id"]),
        document_id=str(chunk.get("document_id", "")),
        filename=chunk.get("filename", ""),
        text=chunk.get("text", ""),
        page=chunk.get("page"),
        section=chunk.get("section"),
        subject=chunk.get("subject", ""),
        semester=int(chunk.get("semester", 0)),
        chunk_index=int(chunk.get("chunk_index", 0)),
    )


class UploadForm(BaseModel):
    subject: str = Field(min_length=1, max_length=120)
    semester: int = Field(ge=1, le=12)
