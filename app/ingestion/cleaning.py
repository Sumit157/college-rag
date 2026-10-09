"""Text cleaning applied after parsing and before chunking."""

from __future__ import annotations

import re

_CONTROL_CHARS = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
_EXCESS_BLANKLINES = re.compile(r"\n{3,}")


def clean_text(text: str) -> str:
    """Normalise line endings, drop control characters and tidy whitespace."""
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = _CONTROL_CHARS.sub("", text)
    lines = [line.rstrip() for line in text.split("\n")]
    text = "\n".join(lines)
    text = _EXCESS_BLANKLINES.sub("\n\n", text)
    return text.strip()


def is_empty_text(text: str) -> bool:
    """True when a string contains no searchable characters."""
    return not text.strip()
