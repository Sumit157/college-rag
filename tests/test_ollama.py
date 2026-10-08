"""Ollama adapter tests using a mocked HTTP transport."""

from __future__ import annotations

import asyncio

import httpx

from app.llm.ollama import OllamaError, OllamaProvider


def _provider(handler) -> OllamaProvider:
    return OllamaProvider(
        base_url="http://ollama.test",
        transport=httpx.MockTransport(handler),
    )


def test_ping_ok() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"models": []})

    assert asyncio.run(_provider(handler).ping()) is True


def test_ping_unreachable() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection refused")

    assert asyncio.run(_provider(handler).ping()) is False


def test_list_models() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        payload = {"models": [{"name": "llama3.2:3b"}, {"name": "nomic-embed-text"}]}
        return httpx.Response(200, json=payload)

    models = asyncio.run(_provider(handler).list_models())
    assert models == ["llama3.2:3b", "nomic-embed-text"]


def test_list_models_raises_when_unreachable() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection refused")

    try:
        asyncio.run(_provider(handler).list_models())
    except OllamaError:
        pass
    else:
        raise AssertionError("expected OllamaError")


def test_health_reports_configured_model_availability() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"models": [{"name": "some-model:latest"}]})

    report = asyncio.run(_provider(handler).health())
    assert report["status"] == "ok"
    assert "models" in report
    assert "llm_model" in report
    assert isinstance(report["configured_model_available"], bool)


def test_health_unavailable_reports_status() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection refused")

    report = asyncio.run(_provider(handler).health())
    assert report["status"] == "unavailable"
    assert report["models"] == []
