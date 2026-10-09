"""Ingestion pipeline: validate → hash → parse → clean → chunk → embed → store."""

from __future__ import annotations

from typing import Any

from app.core.config import get_settings
from app.database.repositories import ChunkRepository, DocumentRepository
from app.embeddings.errors import EmbeddingError
from app.embeddings.provider import EmbeddingProvider
from app.ingestion.cleaning import clean_text, is_empty_text
from app.ingestion.chunking import ChunkDraft, chunk_units
from app.ingestion.errors import (
    DuplicateDocumentError,
    EmptyDocumentError,
    IngestionError,
    CorruptDocumentError,
)
from app.ingestion.hashing import sha256_hex
from app.ingestion.parsers import ParsedUnit, get_parser
from app.ingestion.validation import validate_upload


class IngestionPipeline:
    def __init__(
        self,
        documents: DocumentRepository,
        chunks: ChunkRepository,
        *,
        embeddings: EmbeddingProvider,
        max_upload_bytes: int | None = None,
        chunk_size_tokens: int | None = None,
        chunk_overlap_tokens: int | None = None,
    ) -> None:
        settings = get_settings()
        self._documents = documents
        self._chunks = chunks
        self._embeddings = embeddings
        self._max_upload_bytes = (
            max_upload_bytes if max_upload_bytes is not None else settings.max_upload_size_bytes
        )
        self._chunk_size = chunk_size_tokens or settings.chunk_size_tokens
        self._chunk_overlap = chunk_overlap_tokens or settings.chunk_overlap_tokens

    def ingest(
        self,
        *,
        filename: str,
        data: bytes,
        declared_mime: str | None,
        subject: str,
        semester: int,
    ) -> dict[str, Any]:
        extension = validate_upload(filename, data, declared_mime, self._max_upload_bytes)
        file_hash = sha256_hex(data)

        existing = self._documents.get_by_hash(file_hash)
        if existing is not None:
            raise DuplicateDocumentError(
                f"'{existing.get('filename', filename)}' with the same content is already in your library.",
                existing_id=str(existing["_id"]),
            )

        record = self._documents.create(
            {
                "filename": filename,
                "file_hash": file_hash,
                "file_type": extension.lstrip("."),
                "subject": subject,
                "semester": semester,
                "status": "processing",
                "size_bytes": len(data),
                "chunk_count": 0,
                "page_count": None,
                "error": None,
            }
        )
        document_id = str(record["_id"])

        try:
            units = self._parse_and_clean(extension, data, filename)
            drafts = chunk_units(units, self._chunk_size, self._chunk_overlap)
            if not drafts:
                raise EmptyDocumentError("The document does not contain enough text to index.")
            vectors = self._embed(drafts)

            chunk_records = [
                {
                    "document_id": document_id,
                    "filename": filename,
                    "text": draft.text,
                    "page": draft.page,
                    "section": draft.section,
                    "subject": subject,
                    "semester": semester,
                    "chunk_index": index,
                    "embedding": vectors[index],
                }
                for index, draft in enumerate(drafts)
            ]
            self._chunks.insert_many(chunk_records)

            pages = {unit.page for unit in units if unit.page is not None}
            updated = self._documents.mark_indexed(
                document_id,
                chunk_count=len(chunk_records),
                page_count=len(pages) if pages else None,
            )
            return updated or record
        except EmbeddingError as exc:
            self._documents.mark_failed(document_id, exc.message)
            raise
        except IngestionError as exc:
            self._documents.mark_failed(document_id, exc.message)
            raise
        except Exception:
            message = "The document could not be processed. It may be corrupted."
            self._documents.mark_failed(document_id, message)
            raise CorruptDocumentError(message) from None

    def _embed(self, drafts: list[ChunkDraft]) -> list[list[float]]:
        texts = [draft.text for draft in drafts]
        vectors = self._embeddings.embed(texts)
        if len(vectors) != len(drafts) or any(not vector for vector in vectors):
            raise EmbeddingError(
                "The document could not be prepared for search. Please try again."
            )
        return vectors

    def _parse_and_clean(
        self,
        extension: str,
        data: bytes,
        filename: str,
    ) -> list[ParsedUnit]:
        parser = get_parser(extension)
        raw_units = parser.parse(data, filename)
        units: list[ParsedUnit] = []
        for unit in raw_units:
            text = clean_text(unit.text)
            if not is_empty_text(text):
                units.append(ParsedUnit(text=text, page=unit.page, section=unit.section))
        if not units:
            raise EmptyDocumentError("The document does not contain any readable text.")
        return units
