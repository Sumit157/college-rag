"""Chat engine: retrieve → validate evidence → build context → generate.

The engine never lets the LLM see anything but the supplied context, and it
never lets the LLM produce citation metadata — evidence is assembled by code.
"""

from __future__ import annotations

from app.core.config import get_settings
from app.llm.ollama import OllamaProvider
from app.models.evidence import Evidence
from app.rag.context import build_context
from app.rag.prompts import build_messages
from app.retrieval.retriever import Retriever


class ChatEngine:
    def __init__(
        self,
        retriever: Retriever,
        llm: OllamaProvider,
        relevance_threshold: float | None = None,
        context_max_tokens: int | None = None,
    ) -> None:
        settings = get_settings()
        self._retriever = retriever
        self._llm = llm
        self._threshold = (
            relevance_threshold
            if relevance_threshold is not None
            else settings.relevance_threshold
        )
        self._context_max_tokens = (
            context_max_tokens
            if context_max_tokens is not None
            else settings.context_max_tokens
        )

    def retrieve(
        self,
        *,
        question: str,
        subject: str | None = None,
        semester: int | None = None,
        document_id: str | None = None,
        top_k: int | None = None,
    ) -> list[Evidence]:
        """Retrieve evidence, rejecting anything below the relevance threshold."""
        evidence = self._retriever.retrieve(
            query=question,
            subject=subject,
            semester=semester,
            document_id=document_id,
            top_k=top_k,
        )
        return [item for item in evidence if item.relevance >= self._threshold]

    def build_messages(
        self,
        question: str,
        evidence: list[Evidence],
        history: list[dict] | None = None,
    ) -> list[dict]:
        context = build_context(evidence, self._context_max_tokens)
        return build_messages(question, context, history=history)

    async def generate(self, messages: list[dict]) -> str:
        answer = await self._llm.chat(messages)
        return answer.strip()

    async def generate_stream(self, messages: list[dict]):
        """Yield answer deltas as they are generated."""
        async for token in self._llm.chat_stream(messages):
            yield token
