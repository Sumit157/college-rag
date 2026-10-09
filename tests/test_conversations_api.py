"""API tests for conversation history: save, list, resume, delete."""

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


def test_chat_creates_conversation_and_lists_it(make_client, fake_stack) -> None:
    client = make_client()
    _upload(client)

    response = _ask(
        client, "paging divides physical memory", subject="Operating Systems", semester=5
    )
    assert response.status_code == 200, response.text
    conversation_id = response.json()["conversation_id"]
    assert conversation_id

    listing = client.get("/api/conversations")
    assert listing.status_code == 200
    items = listing.json()["items"]
    assert len(items) == 1
    assert items[0]["id"] == conversation_id
    assert items[0]["title"] == "paging divides physical memory"
    assert items[0]["turn_count"] == 1

    detail = client.get(f"/api/conversations/{conversation_id}")
    assert detail.status_code == 200
    body = detail.json()
    assert body["turn_count"] == 1
    assert body["turns"][0]["id"] == "turn-1"
    assert body["turns"][0]["question"] == "paging divides physical memory"
    assert body["turns"][0]["grounded"] is True
    assert body["turns"][0]["evidence"]
    assert body["turns"][0]["subject"] == "Operating Systems"
    assert body["turns"][0]["semester"] == 5


def test_second_message_appends_to_same_conversation(make_client, fake_stack) -> None:
    client = make_client()
    _upload(client)

    first = _ask(client, "what is paging?").json()
    second = _ask(
        client, "what is virtual memory?", conversation_id=first["conversation_id"]
    ).json()

    assert second["conversation_id"] == first["conversation_id"]
    detail = client.get(f"/api/conversations/{first['conversation_id']}").json()
    assert detail["turn_count"] == 2
    assert [turn["id"] for turn in detail["turns"]] == ["turn-1", "turn-2"]
    assert detail["turns"][1]["question"] == "what is virtual memory?"

    items = client.get("/api/conversations").json()["items"]
    assert len(items) == 1
    assert items[0]["turn_count"] == 2


def test_history_is_replayed_to_the_llm(make_client, fake_stack) -> None:
    client = make_client()
    _upload(client)

    first = _ask(client, "paging divides physical memory").json()
    _ask(
        client,
        "physical memory frames pages",
        conversation_id=first["conversation_id"],
    )

    assert len(fake_stack.chat_calls) == 2
    second_messages = fake_stack.chat_calls[1]
    roles = [m["role"] for m in second_messages]
    assert roles == ["system", "user", "assistant", "user"]
    assert second_messages[1]["content"] == "paging divides physical memory"
    assert second_messages[2]["content"] == fake_stack.answer
    # the current turn still carries retrieved context
    assert "Context:" in second_messages[3]["content"]
    assert second_messages[3]["content"].endswith(
        "Question: physical memory frames pages"
    )


def test_history_turn_limit_is_configurable(make_client, fake_stack) -> None:
    client = make_client(CHAT_HISTORY_TURNS="1")
    _upload(client)

    first = _ask(client, "paging divides physical memory").json()
    _ask(
        client, "physical memory frames pages", conversation_id=first["conversation_id"]
    )
    _ask(
        client, "fixed-size frames called pages", conversation_id=first["conversation_id"]
    )

    roles = [m["role"] for m in fake_stack.chat_calls[2]]
    # only the single most recent prior turn is replayed
    assert roles == ["system", "user", "assistant", "user"]


def test_history_can_be_disabled(make_client, fake_stack) -> None:
    client = make_client(CHAT_HISTORY_TURNS="0")
    _upload(client)

    first = _ask(client, "paging divides physical memory").json()
    _ask(
        client, "physical memory frames pages", conversation_id=first["conversation_id"]
    )

    roles = [m["role"] for m in fake_stack.chat_calls[1]]
    assert roles == ["system", "user"]


def test_invalid_conversation_id_returns_404(make_client, fake_stack) -> None:
    client = make_client()
    _upload(client)

    assert _ask(client, "q", conversation_id="not-an-id").status_code == 404
    assert client.get("/api/conversations/not-an-id").status_code == 404
    assert client.delete("/api/conversations/not-an-id").status_code == 404


def test_missing_context_turn_is_saved(make_client, fake_stack) -> None:
    client = make_client()

    response = _ask(client, "what is paging?")
    body = response.json()
    assert body["grounded"] is False
    assert body["answer"] == MISSING_CONTEXT_MESSAGE

    detail = client.get(f"/api/conversations/{body['conversation_id']}").json()
    assert detail["turn_count"] == 1
    assert detail["turns"][0]["grounded"] is False
    assert detail["turns"][0]["answer"] == MISSING_CONTEXT_MESSAGE
    assert detail["turns"][0]["evidence"] == []

    items = client.get("/api/conversations").json()["items"]
    assert len(items) == 1


def test_llm_failure_saves_no_turn(make_client, fake_stack, monkeypatch) -> None:
    from app.api.routes import chat as chat_route

    client = make_client()
    _upload(client)
    conversation_id = _ask(client, "paging divides physical memory").json()[
        "conversation_id"
    ]

    monkeypatch.setattr(chat_route, "get_llm_provider", lambda: BrokenLLM())
    failed = _ask(
        client, "physical memory frames pages", conversation_id=conversation_id
    )
    assert failed.status_code == 503

    detail = client.get(f"/api/conversations/{conversation_id}").json()
    assert detail["turn_count"] == 1


def test_failed_first_message_hides_empty_conversation(
    make_client, fake_stack, monkeypatch
) -> None:
    from app.api.routes import chat as chat_route

    client = make_client()
    _upload(client)
    monkeypatch.setattr(chat_route, "get_llm_provider", lambda: BrokenLLM())

    response = _ask(client, "paging divides physical memory")
    assert response.status_code == 503

    assert client.get("/api/conversations").json()["items"] == []


def test_stream_saves_turn_and_returns_conversation_id(make_client, fake_stack) -> None:
    client = make_client()
    _upload(client)

    response = client.post(
        "/api/chat/stream", json={"question": "paging divides physical memory"}
    )
    events = _sse_events(response)
    assert events[0]["type"] == "meta"
    conversation_id = events[0]["conversation_id"]
    assert conversation_id
    assert events[-1]["type"] == "done"
    assert events[-1]["conversation_id"] == conversation_id

    detail = client.get(f"/api/conversations/{conversation_id}").json()
    assert detail["turn_count"] == 1
    assert detail["turns"][0]["grounded"] is True

    # continuing the same conversation from the stream endpoint
    response = client.post(
        "/api/chat/stream",
        json={"question": "virtual memory?", "conversation_id": conversation_id},
    )
    events = _sse_events(response)
    assert events[-1]["conversation_id"] == conversation_id
    detail = client.get(f"/api/conversations/{conversation_id}").json()
    assert detail["turn_count"] == 2


def test_delete_conversation(make_client, fake_stack) -> None:
    client = make_client()
    _upload(client)
    conversation_id = _ask(client, "what is paging?").json()["conversation_id"]

    deleted = client.delete(f"/api/conversations/{conversation_id}")
    assert deleted.status_code == 200
    assert deleted.json() == {"deleted": conversation_id}

    assert client.get(f"/api/conversations/{conversation_id}").status_code == 404
    assert client.get("/api/conversations").json()["items"] == []
    assert client.delete(f"/api/conversations/{conversation_id}").status_code == 404
