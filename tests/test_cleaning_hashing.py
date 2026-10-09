"""Hashing, cleaning and section heuristic tests."""

from app.ingestion.cleaning import clean_text, is_empty_text
from app.ingestion.hashing import sha256_hex
from app.ingestion.sections import is_heading


def test_hash_deterministic() -> None:
    assert sha256_hex(b"abc") == sha256_hex(b"abc")


def test_hash_differs_for_different_content() -> None:
    assert sha256_hex(b"abc") != sha256_hex(b"abd")


def test_hash_is_sha256_hex() -> None:
    digest = sha256_hex(b"abc")
    assert len(digest) == 64
    assert all(c in "0123456789abcdef" for c in digest)


def test_clean_normalises_line_endings() -> None:
    assert clean_text("a\r\nb\rc") == "a\nb\nc"


def test_clean_removes_control_chars() -> None:
    assert clean_text("hello\x00\x07 world") == "hello world"


def test_clean_collapses_blank_lines() -> None:
    assert clean_text("a\n\n\n\n\nb") == "a\n\nb"


def test_clean_strips_trailing_whitespace() -> None:
    assert clean_text("line   \nnext\t\n") == "line\nnext"


def test_is_empty_text() -> None:
    assert is_empty_text("   \n  ")
    assert not is_empty_text("x")


def test_numbered_heading_detected() -> None:
    assert is_heading("3. Memory Management")
    assert is_heading("2.1 Virtual Memory")


def test_all_caps_heading_detected() -> None:
    assert is_heading("INTRODUCTION TO PAGING")


def test_title_case_heading_detected() -> None:
    assert is_heading("Memory Management")


def test_sentence_not_heading() -> None:
    assert not is_heading("Paging divides physical memory into frames.")


def test_long_line_not_heading() -> None:
    assert not is_heading("x" * 120)
