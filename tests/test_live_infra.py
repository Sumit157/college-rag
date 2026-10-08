"""Live infrastructure tests.

These verify real MongoDB and Ollama connectivity. They skip automatically
when the service is not running so unit suites stay deterministic.
"""

from __future__ import annotations

import asyncio

import httpx

from app.core.config import get_settings
from app.database.mongo import Mongo
from app.llm.ollama import OllamaProvider


def _mongo_available() -> bool:
    settings = get_settings()
    mongo = Mongo(settings.mongodb_uri, settings.mongodb_database, timeout_ms=2000)
    try:
        return mongo.ping()
    finally:
        mongo.close()


def _ollama_available() -> bool:
    settings = get_settings()
    try:
        response = httpx.get(f"{settings.ollama_base_url}/api/tags", timeout=3.0)
        return response.status_code == 200
    except httpx.HTTPError:
        return False


def test_live_mongo_ping() -> None:
    assert _mongo_available(), "MongoDB is not reachable"


def test_live_ollama_health() -> None:
    if not _ollama_available():
        import pytest

        pytest.skip("Ollama is not running")
    report = asyncio.run(OllamaProvider().health())
    assert report["status"] == "ok"
