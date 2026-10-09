"""Chunking tests: budgets, overlap, page/section preservation."""

from app.ingestion.chunking import ChunkDraft, chunk_text, chunk_units, estimate_tokens
from app.ingestion.parsers import ParsedUnit


def test_estimate_tokens() -> None:
    assert estimate_tokens("") == 0
    assert estimate_tokens("a" * 400) == 100


def test_short_text_single_chunk() -> None:
    chunks = chunk_text("hello world", size_tokens=50, overlap_tokens=10)
    assert chunks == ["hello world"]


def test_long_text_split_within_budget() -> None:
    text = " ".join(f"word{i}" for i in range(2000))
    chunks = chunk_text(text, size_tokens=100, overlap_tokens=20)
    assert len(chunks) > 1
    for chunk in chunks:
        assert estimate_tokens(chunk) <= 100 + 20


def test_overlap_between_consecutive_chunks() -> None:
    text = " ".join(f"word{i}" for i in range(2000))
    chunks = chunk_text(text, size_tokens=100, overlap_tokens=20)
    for previous, current in zip(chunks, chunks[1:]):
        previous_tail = previous.split()[-5:]
        current_head = current.split()[: len(previous_tail) + 5]
        assert any(word in current_head for word in previous_tail)


def test_empty_text_yields_no_chunks() -> None:
    assert chunk_text("   \n ", size_tokens=100, overlap_tokens=10) == []


def _long_units(count: int, page: int | None, section: str | None) -> list[ParsedUnit]:
    return [
        ParsedUnit(
            text=f"Paragraph {index} with enough words to matter for chunking.",
            page=page,
            section=section,
        )
        for index in range(count)
    ]


def test_units_chunked_with_size_limits() -> None:
    units = _long_units(80, page=1, section="Paging")
    drafts = chunk_units(units, size_tokens=60, overlap_tokens=10)
    assert len(drafts) > 1
    for draft in drafts:
        assert isinstance(draft, ChunkDraft)
        assert estimate_tokens(draft.text) <= 70
        assert draft.page == 1
        assert draft.section == "Paging"


def test_chunks_never_cross_page_boundaries() -> None:
    units = (
        _long_units(60, page=1, section="Page One")
        + _long_units(60, page=2, section="Page Two")
    )
    drafts = chunk_units(units, size_tokens=60, overlap_tokens=10)
    assert {d.page for d in drafts} == {1, 2}
    for draft in drafts:
        if draft.page == 1:
            assert "Page Two" not in draft.text
        else:
            assert "Page One" not in draft.text


def test_section_taken_from_first_unit_of_chunk() -> None:
    units = [
        ParsedUnit(text="Alpha section text " * 30, page=3, section="Alpha"),
        ParsedUnit(text="Beta section text " * 30, page=3, section="Beta"),
    ]
    drafts = chunk_units(units, size_tokens=60, overlap_tokens=10)
    assert drafts[0].section == "Alpha"
    assert drafts[-1].section in {"Alpha", "Beta"}


def test_oversized_unit_hard_split() -> None:
    long_text = " ".join(f"bigword{i}" for i in range(3000))
    units = [ParsedUnit(text=long_text, page=7, section="Huge")]
    drafts = chunk_units(units, size_tokens=80, overlap_tokens=15)
    assert len(drafts) > 1
    for draft in drafts:
        assert draft.page == 7
        assert estimate_tokens(draft.text) <= 80 + 15


def test_pageless_units_treated_as_one_document() -> None:
    units = _long_units(100, page=None, section=None)
    drafts = chunk_units(units, size_tokens=60, overlap_tokens=10)
    assert len(drafts) > 1
    assert all(d.page is None for d in drafts)


def test_empty_units_skipped() -> None:
    units = [ParsedUnit(text="   ", page=1, section="X")]
    assert chunk_units(units, size_tokens=50, overlap_tokens=5) == []
