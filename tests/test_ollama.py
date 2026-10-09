"""Ollama adapter tests using a mocked HTTP transport."""

from __future__ import annotations

import asyncio
import json

import httpx
import pytest

from app.llm.ollama import OllamaError, OllamaProvider


def _provider(handler) -> OllamaProvider:
    return OllamaProvider(
        base_url="http://ollama.test",
        transport=httpx.MockTransport(handler),
    )


async def _collect(stream) -> list[str]:
    return [chunk async for chunk in stream]


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


def test_chat_returns_assistant_content() -> None:
    seen: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        seen["path"] = request.url.path
        seen["stream"] = body["stream"]
        seen["temperature"] = body["options"]["temperature"]
        seen["model"] = body["model"]
        return httpx.Response(
            200, json={"message": {"role": "assistant", "content": "Hello!"}}
        )

    messages = [{"role": "user", "content": "hi"}]
    answer = asyncio.run(_provider(handler).chat(messages))

    assert answer == "Hello!"
    assert seen["path"] == "/api/chat"
    assert seen["stream"] is False
    assert seen["temperature"] == 0.2
    assert seen["model"]


def test_chat_empty_response_raises() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"message": {"content": "   "}})

    with pytest.raises(OllamaError):
        asyncio.run(_provider(handler).chat([{"role": "user", "content": "hi"}]))


def test_chat_http_error_raises() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, json={"error": "boom"})

    with pytest.raises(OllamaError):
        asyncio.run(_provider(handler).chat([{"role": "user", "content": "hi"}]))


def test_chat_unreachable_raises() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection refused")

    with pytest.raises(OllamaError):
        asyncio.run(_provider(handler).chat([{"role": "user", "content": "hi"}]))


def test_chat_stream_yields_tokens_in_order() -> None:
    seen: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["stream"] = json.loads(request.content)["stream"]
        lines = [
            json.dumps({"message": {"content": "Pag"}, "done": False}),
            json.dumps({"message": {"content": "ing"}, "done": False}),
            json.dumps({"message": {"content": " works."}, "done": True}),
        ]
        return httpx.Response(200, content=("\n".join(lines) + "\n").encode())

    tokens = asyncio.run(
        _collect(_provider(handler).chat_stream([{"role": "user", "content": "q"}]))
    )

    assert tokens == ["Pag", "ing", " works."]
    assert seen["stream"] is True


def test_chat_stream_http_error_raises() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500)

    with pytest.raises(OllamaError):
        asyncio.run(
            _collect(_provider(handler).chat_stream([{"role": "user", "content": "q"}]))
        )


def test_chat_stream_error_payload_raises() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        line = json.dumps({"error": "model not found"})
        return httpx.Response(200, content=(line + "\n").encode())

    with pytest.raises(OllamaError):
        asyncio.run(
            _collect(_provider(handler).chat_stream([{"role": "user", "content": "q"}]))
        )
