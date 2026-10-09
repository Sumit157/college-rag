"""File validation tests."""

import io
import zipfile

import pytest

from app.ingestion.errors import (
    FileTooLargeError,
    InvalidFileError,
    UnsupportedFileTypeError,
)
from app.ingestion.validation import (
    file_extension,
    validate_content,
    validate_extension,
    validate_mime,
    validate_size,
    validate_upload,
)

MAX = 1024 * 1024


def test_supported_extension_accepted() -> None:
    assert validate_extension("notes.pdf") == ".pdf"
    assert validate_extension("Notes.DOCX") == ".docx"
    assert validate_extension("slides.pptx") == ".pptx"
    assert validate_extension("readme.txt") == ".txt"


def test_unknown_extension_rejected() -> None:
    with pytest.raises(UnsupportedFileTypeError):
        validate_extension("malware.exe")


def test_missing_extension_rejected() -> None:
    with pytest.raises(UnsupportedFileTypeError):
        validate_extension("noextension")


def test_file_extension_normalises_paths() -> None:
    assert file_extension("folder\\notes.pdf") == ".pdf"
    assert file_extension("folder/notes.pdf") == ".pdf"


def test_empty_file_rejected() -> None:
    with pytest.raises(InvalidFileError):
        validate_size(b"", MAX)


def test_oversized_file_rejected() -> None:
    with pytest.raises(FileTooLargeError):
        validate_size(b"x" * (MAX + 1), MAX)


def test_size_within_limit_ok() -> None:
    validate_size(b"x" * 100, MAX)


def test_mime_generic_accepted() -> None:
    validate_mime("notes.pdf", "application/octet-stream")
    validate_mime("notes.pdf", None)


def test_mime_mismatch_rejected() -> None:
    with pytest.raises(InvalidFileError):
        validate_mime("notes.pdf", "text/html")


def test_mime_matching_accepted() -> None:
    validate_mime("notes.pdf", "application/pdf")
    validate_mime("notes.txt", "text/plain; charset=utf-8")


def test_pdf_content_magic() -> None:
    validate_content("notes.pdf", b"%PDF-1.4 rest of file")
    with pytest.raises(InvalidFileError):
        validate_content("notes.pdf", b"just some text")


def test_docx_content_zip_check() -> None:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("word/document.xml", "<w:document/>")
    validate_content("notes.docx", buffer.getvalue())

    with pytest.raises(InvalidFileError):
        validate_content("notes.docx", b"PK\x03\x04 not really a zip")


def test_pptx_missing_part_rejected() -> None:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("other.xml", "<x/>")
    with pytest.raises(InvalidFileError):
        validate_content("deck.pptx", buffer.getvalue())


def test_txt_binary_rejected() -> None:
    with pytest.raises(InvalidFileError):
        validate_content("notes.txt", b"hello\x00world")


def test_txt_masking_other_types_rejected() -> None:
    with pytest.raises(InvalidFileError):
        validate_content("notes.txt", b"%PDF-1.4 masquerading")


def test_validate_upload_happy_path() -> None:
    ext = validate_upload("a.txt", b"hello world", "text/plain", MAX)
    assert ext == ".txt"


def test_validate_upload_wrong_type() -> None:
    with pytest.raises(UnsupportedFileTypeError):
        validate_upload("a.zip", b"PK\x03\x04", "application/zip", MAX)
