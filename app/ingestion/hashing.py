"""Deterministic file hashing for duplicate detection."""

from __future__ import annotations

import hashlib


def sha256_hex(data: bytes) -> str:
    """Return the lowercase hex SHA-256 digest of the file bytes."""
    return hashlib.sha256(data).hexdigest()
