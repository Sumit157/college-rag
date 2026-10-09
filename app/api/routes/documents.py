"""Document management endpoints: upload, list, detail, chunks, delete."""

from __future__ import annotations

import logging

from fastapi import APIRouter, File, Form, HTTPException, Query, UploadFile
from fastapi.concurrency import run_in_threadpool

from app.core.config import get_settings
from app.database.mongo import get_mongo
from app.database.repositories import ChunkRepository, DocumentRepository
from app.embeddings import get_embedding_provider
from app.ingestion.errors import IngestionError
from app.ingestion.pipeline import IngestionPipeline
from app.models.document import (
    ChunkListResponse,
    DeleteResponse,
    DocumentListResponse,
    DocumentOut,
    chunk_to_out,
    document_to_out,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/documents", tags=["documents"])


def _documents_repo() -> DocumentRepository:
    return DocumentRepository(get_mongo().db)


def _chunks_repo() -> ChunkRepository:
    return ChunkRepository(get_mongo().db)


def ensure_indexes() -> None:
    try:
        _documents_repo().ensure_indexes()
    except Exception:
        logger.warning("Could not ensure MongoDB indexes", exc_info=True)


@router.post("", response_model=DocumentOut, status_code=201)
async def create_document(
    file: UploadFile = File(...),
    subject: str = Form(..., min_length=1, max_length=120),
    semester: int = Form(..., ge=1, le=12),
) -> DocumentOut:
    settings = get_settings()
    limit = settings.max_upload_size_bytes

    data = await file.read(limit + 1)

    pipeline = IngestionPipeline(
        documents=_documents_repo(),
        chunks=_chunks_repo(),
        embeddings=get_embedding_provider(),
        max_upload_bytes=limit,
    )
    try:
        record = await run_in_threadpool(
            pipeline.ingest,
            filename=file.filename or "",
            data=data,
            declared_mime=file.content_type,
            subject=subject.strip(),
            semester=semester,
        )
    except IngestionError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from None

    return document_to_out(record)


@router.get("", response_model=DocumentListResponse)
def list_documents(
    subject: str | None = Query(default=None, min_length=1, max_length=120),
    semester: int | None = Query(default=None, ge=1, le=12),
) -> DocumentListResponse:
    docs = _documents_repo().list(subject=subject, semester=semester)
    items = [document_to_out(doc) for doc in docs]
    return DocumentListResponse(items=items, total=len(items))


@router.get("/{document_id}", response_model=DocumentOut)
def get_document(document_id: str) -> DocumentOut:
    doc = _documents_repo().get(document_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="Document not found.")
    return document_to_out(doc)


@router.get("/{document_id}/chunks", response_model=ChunkListResponse)
def list_document_chunks(
    document_id: str,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> ChunkListResponse:
    if _documents_repo().get(document_id) is None:
        raise HTTPException(status_code=404, detail="Document not found.")
    items, total = _chunks_repo().list_by_document(document_id, limit=limit, offset=offset)
    return ChunkListResponse(items=[chunk_to_out(c) for c in items], total=total)


@router.delete("/{document_id}", response_model=DeleteResponse)
def delete_document(document_id: str) -> DeleteResponse:
    repo = _documents_repo()
    if repo.get(document_id) is None:
        raise HTTPException(status_code=404, detail="Document not found.")
    repo.delete(document_id)
    return DeleteResponse(deleted=document_id)
