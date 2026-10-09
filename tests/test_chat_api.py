"""API tests for chat: grounded answers, missing-context, streaming."""

from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient

from app.llm.ollama import OllamaError
from app.rag.prompts import MISSING_CONTEXT_MESSAGE

from tests.conftest import FakeEmbeddingProvider, build_txt


class FakeLLM:
    def __init__(self, answer: str = "Paging divides memory into fixed-size frames [1].") -> None:
        self.answer = answer
        self.chat_calls: list[list[dict]] = []
        self.stream_calls: list[list[dict]] = []

    async def chat(self, messages, temperature=None) -> str:
        self.chat_calls.append(messages)
        return self.answer

    async def chat_stream(self, messages, temperature=None):
        self.stream_calls.append(messages)
        for token in ["Paging divides ", "frames [1]."]:
            yield token


class BrokenLLM:
    async def chat(self, messages, temperature=None) -> str:
        raise OllamaError("generation failed")

    async def chat_stream(self, messages, temperature=None):
        raise OllamaError("generation failed")
        yield  # pragma: no cover


@pytest.fixture(autouse=True)
def fake_stack(monkeypatch):
    """Fake embeddings + fake LLM so chat tests never touch Ollama."""
    from app.api.routes import chat as chat_route
    from app.api.routes import documents as documents_route

    fake_llm = FakeLLM()
    fake_embeddings = FakeEmbeddingProvider()
    monkeypatch.setattr(documents_route, "get_embedding_provider", lambda: fake_embeddings)
    monkeypatch.setattr(chat_route, "get_embedding_provider", lambda: fake_embeddings)
    monkeypatch.setattr(chat_route, "get_llm_provider", lambda: fake_llm)
    return fake_llm


def _upload(client: TestClient) -> dict:
    files = {"file": ("os.txt", build_txt(), "text/plain")}
    data = {"subject": "Operating Systems", "semester": "5"}
    response = client.post("/api/documents", files=files, data=data)
    assert response.status_code == 201, response.text
    return response.json()


def _ask(client: TestClient, question: str, **extra):
    return client.post("/api/chat", json={"question": question, **extra})


def _sse_events(response) -> list[dict]:
    events = []
    for line in response.text.split("\n"):
        if line.startswith("data: "):
            events.append(json.loads(line[len("data: "):]))
    return events


def test_chat_returns_grounded_answer_with_evidence(make_client, fake_stack) -> None:
    client = make_client()
    _upload(client)

    response = _ask(client, "paging divides physical memory")

    assert response.status_code == 200, response.text
    body = response.json()
    assert set(body) == {"answer", "evidence", "grounded", "conversation_id"}
    assert body["grounded"] is True
    assert body["conversation_id"]
    assert body["answer"] == "Paging divides memory into fixed-size frames [1]."
    assert body["evidence"]
    assert body["evidence"][0]["filename"] == "os.txt"
    assert body["evidence"][0]["id"] == "evidence-1"

    assert fake_stack.chat_calls, "LLM should have been called"
    messages = fake_stack.chat_calls[0]
    assert [m["role"] for m in messages] == ["system", "user"]
    assert "ONLY knowledge source" in messages[0]["content"]
    assert "os.txt" in messages[1]["content"]


def test_chat_without_documents_returns_missing_context(make_client, fake_stack) -> None:
    client = make_client()

    response = _ask(client, "what is paging?")

    assert response.status_code == 200
    body = response.json()
    assert body["answer"] == MISSING_CONTEXT_MESSAGE
    assert body["grounded"] is False
    assert body["evidence"] == []
    # the LLM must not be called when there is no evidence
    assert fake_stack.chat_calls == []


def test_chat_rejects_blank_question(make_client) -> None:
    client = make_client()
    assert _ask(client, "").status_code == 422
    assert _ask(client, "   ").status_code == 422


def test_chat_llm_failure_returns_friendly_503(make_client, monkeypatch) -> None:
    from app.api.routes import chat as chat_route

    monkeypatch.setattr(chat_route, "get_llm_provider", lambda: BrokenLLM())
    client = make_client()
    _upload(client)

    response = _ask(client, "paging divides physical memory")

    assert response.status_code == 503
    assert "unavailable" in response.json()["detail"].lower()
    assert "Traceback" not in response.text


def test_chat_stream_emits_meta_tokens_done(make_client, fake_stack) -> None:
    client = make_client()
    _upload(client)

    response = client.post(
        "/api/chat/stream", json={"question": "paging divides physical memory"}
    )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")

    events = _sse_events(response)
    assert [e["type"] for e in events] == ["meta", "token", "token", "done"]

    meta = events[0]
    assert meta["grounded"] is True
    assert meta["evidence"][0]["filename"] == "os.txt"
    assert meta["conversation_id"]

    tokens = [e["text"] for e in events[1:-1]]
    assert "".join(tokens) == "Paging divides frames [1]."

    done = events[-1]
    assert done["answer"] == "Paging divides frames [1]."
    assert done["grounded"] is True
    assert done["evidence"][0]["id"] == "evidence-1"
    assert done["conversation_id"] == meta["conversation_id"]
    assert fake_stack.stream_calls


def test_chat_stream_without_documents(make_client, fake_stack) -> None:
    client = make_client()

    response = client.post("/api/chat/stream", json={"question": "what is paging?"})

    assert response.status_code == 200
    events = _sse_events(response)
    assert [e["type"] for e in events] == ["meta", "done"]
    assert events[0]["grounded"] is False
    assert events[0]["evidence"] == []
    assert events[1]["answer"] == MISSING_CONTEXT_MESSAGE
    assert events[1]["grounded"] is False
    assert fake_stack.stream_calls == []


def test_chat_stream_llm_failure_emits_error_event(make_client, monkeypatch) -> None:
    from app.api.routes import chat as chat_route

    monkeypatch.setattr(chat_route, "get_llm_provider", lambda: BrokenLLM())
    client = make_client()
    _upload(client)

    response = client.post(
        "/api/chat/stream", json={"question": "paging divides physical memory"}
    )

    assert response.status_code == 200
    events = _sse_events(response)
    types = [e["type"] for e in events]
    assert "error" in types
    assert "done" not in types
    error = next(e for e in events if e["type"] == "error")
    assert "unavailable" in error["detail"].lower()
    assert "Traceback" not in response.text
