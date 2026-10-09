"""Configurable text chunking that preserves page and section boundaries.

Units produced by the parsers are grouped per page (or per document when
the source has no pages). Chunks are assembled from whole units up to the
configured token budget, with a shared tail (overlap) carried into the next
chunk. Oversized single units are hard-split on word boundaries.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Sequence

from app.ingestion.parsers import ParsedUnit

CHARS_PER_TOKEN = 4


def estimate_tokens(text: str) -> int:
    """Cheap token estimate (~4 characters per token)."""
    return math.ceil(len(text) / CHARS_PER_TOKEN) if text else 0


@dataclass
class ChunkDraft:
    text: str
    page: int | None
    section: str | None


def _tail_overlap(text: str, overlap_tokens: int) -> str:
    """Return the trailing portion of ``text`` worth roughly overlap tokens."""
    if overlap_tokens <= 0:
        return ""
    budget = overlap_tokens * CHARS_PER_TOKEN
    if len(text) <= budget:
        return text.strip()
    tail = text[-budget:]
    space = tail.find(" ")
    if 0 < space < budget // 2:
        tail = tail[space + 1 :]
    return tail.strip()


def _split_long_text(text: str, size_tokens: int, overlap_tokens: int) -> list[str]:
    """Hard-split a single unit that exceeds the chunk budget."""
    words = text.split()
    if not words:
        return []
    target_chars = size_tokens * CHARS_PER_TOKEN
    chunks: list[str] = []
    start = 0
    while start < len(words):
        end = start + 1
        while end < len(words) and len(" ".join(words[start:end])) < target_chars:
            end += 1
        piece = " ".join(words[start:end])
        chunks.append(piece)
        if end >= len(words):
            break
        overlap_tail = _tail_overlap(piece, overlap_tokens)
        next_start = end
        if overlap_tail:
            overlap_words = overlap_tail.split()
            back = len(overlap_words)
            if end - back > start:
                next_start = end - back
        start = max(next_start, start + 1)
    return chunks


def chunk_text(text: str, size_tokens: int, overlap_tokens: int) -> list[str]:
    """Split free text into token-budget chunks with overlap."""
    if not text.strip():
        return []
    if estimate_tokens(text) <= size_tokens:
        return [text.strip()]
    return _split_long_text(text, size_tokens, overlap_tokens)


def _group_by_page(units: Sequence[ParsedUnit]) -> list[list[ParsedUnit]]:
    groups: list[list[ParsedUnit]] = []
    current_key: object = object()
    for unit in units:
        key = unit.page
        if key != current_key or not groups:
            groups.append([])
            current_key = key
        groups[-1].append(unit)
    return groups


def chunk_units(
    units: Sequence[ParsedUnit],
    size_tokens: int,
    overlap_tokens: int,
) -> list[ChunkDraft]:
    """Turn parsed units into chunk drafts, never crossing page boundaries."""
    drafts: list[ChunkDraft] = []
    target_chars = size_tokens * CHARS_PER_TOKEN

    for group in _group_by_page(units):
        page = group[0].page
        section = group[0].section

        current_parts: list[str] = []
        current_chars = 0
        carry = ""

        def emit() -> None:
            nonlocal current_parts, current_chars, carry, section
            if not current_parts:
                return
            body = "\n\n".join(current_parts).strip()
            full = f"{carry}\n\n{body}".strip() if carry else body
            if full:
                drafts.append(ChunkDraft(text=full, page=page, section=section))
            carry = _tail_overlap(full, overlap_tokens)
            current_parts = []
            current_chars = 0

        for unit in group:
            unit_text = unit.text.strip()
            if not unit_text:
                continue

            if estimate_tokens(unit_text) > size_tokens:
                emit()
                for piece in _split_long_text(unit_text, size_tokens, overlap_tokens):
                    drafts.append(ChunkDraft(text=piece, page=page, section=unit.section))
                carry = ""
                section = None
                continue

            unit_chars = len(unit_text) + (len("\n\n") if current_parts else 0)
            if current_parts and current_chars + unit_chars > target_chars - len(carry):
                emit()
                section = unit.section or section

            if not current_parts:
                section = unit.section if unit.section is not None else section
            current_parts.append(unit_text)
            current_chars += unit_chars

        emit()

    return drafts
