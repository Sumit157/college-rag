"""Upload validation: extension, MIME advisory check and content sniffing.

Uploaded bytes are never trusted: the extension must be supported, the
declared MIME type must not contradict it, and the file content must match
the expected format (magic bytes / container structure).
"""

from __future__ import annotations

import io
import mimetypes
import zipfile
from pathlib import PurePosixPath

from app.ingestion.errors import (
    FileTooLargeError,
    InvalidFileError,
    UnsupportedFileTypeError,
)

SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".pptx", ".txt"}

_GENERIC_MIMES = {
    "application/octet-stream",
    "binary/octet-stream",
    "",
}

_ALLOWED_MIME_PREFIXES = {
    ".pdf": ["application/pdf"],
    ".docx": [
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/zip",
        "application/x-zip-compressed",
    ],
    ".pptx": [
        "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        "application/vnd.ms-powerpoint",
        "application/zip",
        "application/x-zip-compressed",
    ],
    ".txt": ["text/plain", "text/markdown"],
}


def file_extension(filename: str | None) -> str:
    if not filename:
        return ""
    return PurePosixPath(filename.replace("\\", "/")).suffix.lower()


def validate_size(data: bytes, max_bytes: int) -> None:
    if len(data) == 0:
        raise InvalidFileError("The uploaded file is empty.")
    if len(data) > max_bytes:
        raise FileTooLargeError(
            f"The file exceeds the maximum upload size of {max_bytes // (1024 * 1024)} MB."
        )


def validate_extension(filename: str | None) -> str:
    ext = file_extension(filename)
    if not filename or not ext:
        raise UnsupportedFileTypeError(
            "The file has no extension. Supported types: PDF, DOCX, PPTX, TXT."
        )
    if ext not in SUPPORTED_EXTENSIONS:
        raise UnsupportedFileTypeError(
            f"Unsupported file type '{ext}'. Supported types: PDF, DOCX, PPTX, TXT."
        )
    return ext


def validate_mime(filename: str, declared_mime: str | None) -> None:
    """Reject declared MIME types that clearly contradict the extension.

    Generic values (``application/octet-stream``) and missing values are
    accepted; the byte-level sniffing in :func:`validate_content` is
    authoritative.
    """
    if not declared_mime:
        return
    mime = declared_mime.split(";")[0].strip().lower()
    if mime in _GENERIC_MIMES:
        return
    ext = file_extension(filename)
    allowed = _ALLOWED_MIME_PREFIXES.get(ext, [])
    if any(mime == a or mime.startswith(a) for a in allowed):
        return
    expected, _ = mimetypes.guess_type(filename)
    if expected and mime == expected:
        return
    raise InvalidFileError(
        f"The declared content type '{mime}' does not match a {ext} file."
    )


def validate_content(filename: str, data: bytes) -> None:
    ext = file_extension(filename)
    if ext == ".pdf":
        if not data.startswith(b"%PDF"):
            raise InvalidFileError("The file does not look like a valid PDF.")
        return
    if ext in {".docx", ".pptx"}:
        if not zipfile.is_zipfile(io.BytesIO(data)):
            raise InvalidFileError(f"The {ext[1:].upper()} file is corrupted or not a ZIP container.")
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            names = set(archive.namelist())
        if ext == ".docx" and "word/document.xml" not in names:
            raise InvalidFileError("The DOCX file is missing its main document part.")
        if ext == ".pptx" and "ppt/presentation.xml" not in names:
            raise InvalidFileError("The PPTX file is missing its main presentation part.")
        return
    if ext == ".txt":
        head = data[:8192]
        if b"\x00" in head:
            raise InvalidFileError(
                "The file contains binary data and is not a readable text file."
            )
        if head.startswith(b"%PDF") or head.startswith(b"PK\x03\x04"):
            raise InvalidFileError(
                "The file content does not match the TXT extension."
            )


def validate_upload(
    filename: str | None,
    data: bytes,
    declared_mime: str | None,
    max_bytes: int,
) -> str:
    """Run the full validation chain and return the normalised extension."""
    ext = validate_extension(filename)
    validate_size(data, max_bytes)
    assert filename is not None
    validate_mime(filename, declared_mime)
    validate_content(filename, data)
    return ext
