"""Ingestion errors with user-safe messages and HTTP status codes."""

from __future__ import annotations


class IngestionError(Exception):
    status_code = 400

    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(message)


class InvalidFileError(IngestionError):
    status_code = 400


class UnsupportedFileTypeError(IngestionError):
    status_code = 415


class FileTooLargeError(IngestionError):
    status_code = 413


class CorruptDocumentError(IngestionError):
    status_code = 400


class EmptyDocumentError(IngestionError):
    status_code = 400


class DuplicateDocumentError(IngestionError):
    status_code = 409

    def __init__(self, message: str, existing_id: str | None = None) -> None:
        super().__init__(message)
        self.existing_id = existing_id
