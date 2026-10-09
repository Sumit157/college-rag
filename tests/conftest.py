"""Shared test helpers and fixtures."""

from __future__ import annotations

import io
import os

import pytest

from app.core.config import get_settings
from app.database.mongo import Mongo, close_mongo

TEST_DB = "college_rag_test"


def mongo_available(timeout_ms: int = 2000) -> bool:
    settings = get_settings()
    mongo = Mongo(settings.mongodb_uri, TEST_DB, timeout_ms=timeout_ms)
    try:
        return mongo.ping()
    finally:
        mongo.close()


def drop_test_db() -> None:
    settings = get_settings()
    mongo = Mongo(settings.mongodb_uri, TEST_DB, timeout_ms=2000)
    try:
        mongo.client.drop_database(TEST_DB)
    finally:
        mongo.close()


class FakeEmbeddingProvider:
    """Deterministic hashed bag-of-words embeddings for hermetic tests.

    Shared vocabulary produces similar vectors, so ranking assertions behave
    like a real embedding model without calling Ollama.
    """

    def __init__(self, dim: int = 32) -> None:
        self._dim = dim
        self.model = "fake-embedding"

    def embed(self, texts: list[str]) -> list[list[float]]:
        return [self._vector(text) for text in texts]

    def embed_query(self, text: str) -> list[float]:
        return self._vector(text)

    def _vector(self, text: str) -> list[float]:
        import hashlib
        import math
        import re

        vector = [0.0] * self._dim
        for token in re.findall(r"[a-z0-9]+", text.lower()):
            index = int(hashlib.md5(token.encode()).hexdigest(), 16) % self._dim
            vector[index] += 1.0
        norm = math.sqrt(sum(value * value for value in vector))
        if norm:
            vector = [value / norm for value in vector]
        return vector


@pytest.fixture
def make_client():
    """Create TestClient instances bound to an isolated test database."""
    from fastapi.testclient import TestClient

    from app.main import app

    if not mongo_available():
        pytest.skip("MongoDB is not running")

    clients: list[TestClient] = []
    original_env: dict[str, str | None] = {}
    touched_keys: set[str] = set()

    def _make(**env_vars: str) -> TestClient:
        close_mongo()
        keys = {"MONGODB_DATABASE", *env_vars.keys()}
        for key in keys:
            if key not in touched_keys:
                original_env[key] = os.environ.get(key)
                touched_keys.add(key)
            os.environ[key] = TEST_DB if key == "MONGODB_DATABASE" else env_vars.get(key, "")
        for key, value in env_vars.items():
            os.environ[key] = value
        get_settings.cache_clear()
        client = TestClient(app)
        client.__enter__()
        clients.append(client)
        return client

    yield _make

    for client in clients:
        try:
            client.__exit__(None, None, None)
        except Exception:
            pass
    close_mongo()
    get_settings.cache_clear()
    drop_test_db()
    for key in touched_keys:
        original = original_env.get(key)
        if original is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = original
    get_settings.cache_clear()


def build_pdf(pages: list[str]) -> bytes:
    import pymupdf

    doc = pymupdf.open()
    for text in pages:
        page = doc.new_page()
        page.insert_text((72, 72), text, fontsize=12)
    data = doc.tobytes()
    doc.close()
    return data


def build_docx() -> bytes:
    import docx

    document = docx.Document()
    document.add_heading("Operating Systems", level=0)
    document.add_paragraph("Processes and threads are fundamental OS concepts.")
    document.add_heading("Paging", level=1)
    document.add_paragraph(
        "Paging divides physical memory into fixed-size frames called pages."
    )
    table = document.add_table(rows=2, cols=2)
    table.cell(0, 0).text = "Term"
    table.cell(0, 1).text = "Meaning"
    table.cell(1, 0).text = "Frame"
    table.cell(1, 1).text = "A fixed-size block of physical memory"
    buffer = io.BytesIO()
    document.save(buffer)
    return buffer.getvalue()


def build_pptx() -> bytes:
    from pptx import Presentation

    presentation = Presentation()
    slide = presentation.slides.add_slide(presentation.slide_layouts[1])
    slide.shapes.title.text = "Paging"
    slide.placeholders[1].text = (
        "Paging divides physical memory into fixed-size frames called pages."
    )
    slide2 = presentation.slides.add_slide(presentation.slide_layouts[1])
    slide2.shapes.title.text = "Segmentation"
    slide2.placeholders[1].text = "Segmentation splits memory into variable-size segments."
    buffer = io.BytesIO()
    presentation.save(buffer)
    return buffer.getvalue()


def build_txt() -> bytes:
    return (
        "1. Introduction\n"
        "Operating systems manage hardware and software resources.\n"
        "\n"
        "2. Paging\n"
        "Paging divides physical memory into fixed-size frames called pages.\n"
        "Virtual addresses are mapped to physical frames by the MMU.\n"
    ).encode("utf-8")
