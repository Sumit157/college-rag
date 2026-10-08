"""Health endpoint tests (dependencies are mocked; no live services needed)."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import app


class FakeMongo:
    def __init__(self, ok: bool = True) -> None:
        self._ok = ok

    def ping(self) -> bool:
        return self._ok


OK_REPORT = {
    "status": "ok",
    "url": "http://localhost:11434",
    "models": ["llama3.2:3b"],
    "llm_model": "llama3.2:3b",
    "embedding_model": "nomic-embed-text",
    "configured_model_available": True,
}


@pytest.fixture
def client(monkeypatch) -> TestClient:
    from app.api.routes import health as health_route

    monkeypatch.setattr(health_route, "get_mongo", lambda: FakeMongo(True))
    monkeypatch.setattr(
        health_route,
        "OllamaProvider",
        type(
            "FakeOllama",
            (),
            {"health": staticmethod(lambda: _async_report(OK_REPORT))},
        ),
    )
    with TestClient(app) as test_client:
        yield test_client


async def _async_report(report: dict) -> dict:
    return report


def test_health_ok(client: TestClient) -> None:
    response = client.get("/api/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["mongo"]["status"] == "ok"
    assert body["ollama"]["status"] == "ok"
    assert body["app"]


def test_health_degraded_when_mongo_down(monkeypatch) -> None:
    from app.api.routes import health as health_route

    monkeypatch.setattr(health_route, "get_mongo", lambda: FakeMongo(False))
    monkeypatch.setattr(
        health_route,
        "OllamaProvider",
        type("FakeOllama", (), {"health": staticmethod(lambda: _async_report(OK_REPORT))}),
    )
    with TestClient(app) as client:
        response = client.get("/api/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "degraded"
    assert body["mongo"]["status"] == "unavailable"
    assert body["ollama"]["status"] == "ok"


def test_health_degraded_when_ollama_down(monkeypatch) -> None:
    from app.api.routes import health as health_route

    down_report = {"status": "unavailable", "url": "http://localhost:11434", "models": []}
    monkeypatch.setattr(health_route, "get_mongo", lambda: FakeMongo(True))
    monkeypatch.setattr(
        health_route,
        "OllamaProvider",
        type(
            "FakeOllama",
            (),
            {"health": staticmethod(lambda: _async_report(down_report))},
        ),
    )
    with TestClient(app) as client:
        response = client.get("/api/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "degraded"
    assert body["ollama"]["status"] == "unavailable"


def test_no_stack_traces_in_response(client: TestClient) -> None:
    body = client.get("/api/health").text
    assert "Traceback" not in body
    assert 'File "' not in body
