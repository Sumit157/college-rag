"""Unit tests for context building, grounded prompting and the chat engine."""

from __future__ import annotations

import pytest

from app.models.evidence import Evidence
from app.rag.context import build_context
from app.rag.engine import ChatEngine
from app.rag.prompts import MISSING_CONTEXT_MESSAGE, SYSTEM_PROMPT, build_messages


def _ev(text: str, relevance: float = 0.9, **overrides) -> Evidence:
    fields = {
        "id": "evidence-1",
        "document_id": "doc-1",
        "filename": "os.txt",
        "page": 42,
        "section": "Memory Management",
        "chunk_id": "chunk-1",
        "text": text,
        "relevance": relevance,
    }
    fields.update(overrides)
    return Evidence(**fields)


class StubRetriever:
    def __init__(self, results: list[Evidence]) -> None:
        self.results = results
        self.last_kwargs: dict | None = None

    def retrieve(self, **kwargs) -> list[Evidence]:
        self.last_kwargs = kwargs
        return self.results


class FakeLLM:
    def __init__(self, answer: str = "The answer.") -> None:
        self.answer = answer
        self.calls: list[list[dict]] = []

    async def chat(self, messages, temperature=None) -> str:
        self.calls.append(messages)
        return self.answer


def test_context_numbers_sources_with_metadata() -> None:
    evidence = [_ev("first"), _ev("second", id="evidence-2", chunk_id="chunk-2")]
    messages = build_messages("q", evidence)

    user = messages[1]["content"]
    assert "[1] os.txt | page 42 | section Memory Management" in user
    assert "[2] os.txt | page 42 | section Memory Management" in user
    assert "first" in user and "second" in user


def test_context_deduplicates_repeated_text() -> None:
    evidence = [
        _ev("identical text"),
        _ev("Identical   Text", id="evidence-2", chunk_id="chunk-2"),
        _ev("different", id="evidence-3", chunk_id="chunk-3"),
    ]
    selected = build_context(evidence, max_tokens=10_000)
    assert [item.text for item in selected] == ["identical text", "different"]


def test_context_fits_token_budget() -> None:
    # each block is ~510 estimated tokens; budget fits only the first one
    evidence = [_ev("word " * 400), _ev("more " * 400, id="evidence-2", chunk_id="c2")]
    selected = build_context(evidence, max_tokens=600)
    assert len(selected) == 1
    assert selected[0].text == evidence[0].text


def test_context_always_includes_first_chunk_even_when_oversized() -> None:
    evidence = [_ev("huge " * 2000)]
    selected = build_context(evidence, max_tokens=50)
    assert len(selected) == 1
    assert len(selected[0].text) < len(evidence[0].text)
    assert selected[0].text.endswith("...")


def test_system_prompt_enforces_grounding() -> None:
    assert "ONLY knowledge source" in SYSTEM_PROMPT
    assert MISSING_CONTEXT_MESSAGE in SYSTEM_PROMPT
    assert "Never invent" in SYSTEM_PROMPT
    assert "Do not reveal your reasoning" in SYSTEM_PROMPT


def test_build_messages_shape() -> None:
    messages = build_messages("What is paging?", [_ev("Paging divides memory.")])
    assert [m["role"] for m in messages] == ["system", "user"]
    assert messages[0]["content"] == SYSTEM_PROMPT
    assert "What is paging?" in messages[1]["content"]
    assert "Context:" in messages[1]["content"]


def test_engine_filters_low_relevance_evidence() -> None:
    retriever = StubRetriever(
        [
            _ev("relevant", relevance=0.8),
            _ev("noise", relevance=0.2, id="evidence-2", chunk_id="c2"),
        ]
    )
    engine = ChatEngine(
        retriever=retriever, llm=FakeLLM(), relevance_threshold=0.4
    )

    evidence = engine.retrieve(question="q")

    assert [item.text for item in evidence] == ["relevant"]


def test_engine_passes_metadata_filters_through() -> None:
    retriever = StubRetriever([])
    engine = ChatEngine(retriever=retriever, llm=FakeLLM())

    engine.retrieve(question="q", subject="DBMS", semester=5, document_id="d9", top_k=3)

    assert retriever.last_kwargs == {
        "query": "q",
        "subject": "DBMS",
        "semester": 5,
        "document_id": "d9",
        "top_k": 3,
    }


def test_engine_generate_returns_stripped_answer() -> None:
    llm = FakeLLM(answer="  Paging is memory mapping. \n")
    engine = ChatEngine(retriever=StubRetriever([]), llm=llm)
    messages = [{"role": "user", "content": "q"}]

    import asyncio

    answer = asyncio.run(engine.generate(messages))
    assert answer == "Paging is memory mapping."
    assert llm.calls == [messages]


def test_engine_respects_context_token_budget() -> None:
    engine = ChatEngine(
        retriever=StubRetriever([]),
        llm=FakeLLM(),
        context_max_tokens=100,
    )
    evidence = [_ev("padding " * 1000)]

    messages = engine.build_messages("q", evidence)

    assert "[1] os.txt" in messages[1]["content"]
    assert len(messages[1]["content"]) < len(evidence[0].text)
