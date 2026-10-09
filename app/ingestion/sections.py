"""Section detection heuristics for plain-text style sources (PDF/TXT).

Parsers that have real structure (DOCX heading styles, PPTX slide titles)
do not need these heuristics.
"""

from __future__ import annotations

import re

_NUMBERED_HEADING = re.compile(r"^\d+(\.\d+)*\.?\s+\S")
_SMALL_WORDS = {"and", "or", "of", "the", "a", "an", "in", "on", "for", "to", "with"}


def is_heading(line: str) -> bool:
    """Heuristic: does this single line look like a section heading?"""
    s = line.strip()
    if not s or len(s) > 100:
        return False
    if s.endswith((".", ",", ";", "!", "?", ":")):
        return False
    if s.startswith("#"):
        return True
    if _NUMBERED_HEADING.match(s):
        return True

    letters = [c for c in s if c.isalpha()]
    if len(letters) >= 2 and all(c.isupper() for c in letters):
        return True

    words = [w for w in s.split() if any(c.isalpha() for c in w)]
    if 1 <= len(words) <= 8 and sum(len(w) for w in s) <= 60:
        if all(w[0].isupper() for w in words if w.lower() not in _SMALL_WORDS):
            return True
    return False
