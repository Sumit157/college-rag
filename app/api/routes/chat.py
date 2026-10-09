"""Chat endpoints: grounded Q&A over uploaded documents (JSON + streaming)."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import StreamingResponse

from app.core.config import get_settings
from app.database.mongo import get_mongo
from app.database.repositories import ConversationRepository
from app.embeddings.errors import EmbeddingError
from app.embeddings.provider import get_embedding_provider
from app.llm.ollama import OllamaError, get_llm_provider
from app.models.chat import ChatRequest, ChatResponse
from app.models.evidence import Evidence
from app.rag.engine import ChatEngine
from app.rag.prompts import MISSING_CONTEXT_MESSAGE
from app.retrieval.retriever import Retriever
from app.retrieval.vector_store import RetrievalError, get_vector_store

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chat", tags=["chat"])

LLM_UNAVAILABLE = "The assistant is temporarily unavailable. Please try again in a moment."
TITLE_MAX_CHARS = 80


def _engine() -> ChatEngine:
    settings = get_settings()
    retriever = Retriever(
        embeddings=get_embedding_provider(),
        store=get_vector_store(),
        default_top_k=settings.retrieval_top_k,
    )
    return ChatEngine(retriever=retriever, llm=get_llm_provider())


def _validate(question: str) -> str:
    question = question.strip()
    if not question:
        raise HTTPException(status_code=422, detail="The question must not be empty.")
    return question


async def _retrieve(engine: ChatEngine, question: str, request: ChatRequest) -> list[Evidence]:
    try:
        return await run_in_threadpool(
            engine.retrieve,
            question=question,
            subject=request.subject,
            semester=request.semester,
            document_id=request.document_id,
            top_k=request.top_k,
        )
    except EmbeddingError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from None
    except RetrievalError as exc:
        raise HTTPException(status_code=503, detail=exc.message) from None


def _conversations_repo() -> ConversationRepository:
    return ConversationRepository(get_mongo().db)


async def _resolve_conversation(conversation_id: str | None, question: str) -> dict:
    """Load the requested conversation, or start a new one titled by the question."""
    repo = _conversations_repo()
    if conversation_id:
        doc = await run_in_threadpool(repo.get, conversation_id)
        if doc is None:
            raise HTTPException(status_code=404, detail="Conversation not found.")
        return doc
    title = question if len(question) <= TITLE_MAX_CHARS else question[: TITLE_MAX_CHARS - 1] + "…"
    return await run_in_threadpool(repo.create, title)


def _history(conversation: dict) -> list[dict]:
    """Prior turns replayed to the LLM, most recent first, capped by config."""
    limit = get_settings().chat_history_turns
    if limit <= 0:
        return []
    turns = conversation.get("turns", [])[-limit:]
    return [
        {"question": turn.get("question", ""), "answer": turn.get("answer", "")}
        for turn in turns
    ]


async def _append_turn(
    conversation: dict,
    request: ChatRequest,
    *,
    question: str,
    answer: str,
    grounded: bool,
    evidence: list[Evidence],
) -> str:
    repo = _conversations_repo()
    turn = {
        "id": f"turn-{int(conversation.get('turn_count', 0)) + 1}",
        "question": question,
        "answer": answer,
        "grounded": grounded,
        "evidence": [item.model_dump() for item in evidence],
        "subject": request.subject,
        "semester": request.semester,
        "document_id": request.document_id,
        "created_at": datetime.now(timezone.utc),
    }
    updated = await run_in_threadpool(
        repo.append_turn, str(conversation["_id"]), turn
    )
    if updated is None:
        raise HTTPException(status_code=404, detail="Conversation not found.")
    return str(conversation["_id"])


@router.post("", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    question = _validate(request.question)
    conversation = await _resolve_conversation(request.conversation_id, question)
    conversation_id = str(conversation["_id"])
    history = _history(conversation)

    engine = _engine()
    evidence = await _retrieve(engine, question, request)
    if not evidence:
        await _append_turn(
            conversation,
            request,
            question=question,
            answer=MISSING_CONTEXT_MESSAGE,
            grounded=False,
            evidence=[],
        )
        return ChatResponse(
            answer=MISSING_CONTEXT_MESSAGE,
            evidence=[],
            grounded=False,
            conversation_id=conversation_id,
        )

    messages = engine.build_messages(question, evidence, history=history)
    try:
        answer = await engine.generate(messages)
    except OllamaError:
        raise HTTPException(status_code=503, detail=LLM_UNAVAILABLE) from None
    if not answer:
        raise HTTPException(status_code=503, detail=LLM_UNAVAILABLE)
    await _append_turn(
        conversation,
        request,
        question=question,
        answer=answer,
        grounded=True,
        evidence=evidence,
    )
    return ChatResponse(
        answer=answer,
        evidence=evidence,
        grounded=True,
        conversation_id=conversation_id,
    )


def _sse(payload: dict) -> str:
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"


@router.post("/stream")
async def chat_stream(request: ChatRequest) -> StreamingResponse:
    question = _validate(request.question)
    conversation = await _resolve_conversation(request.conversation_id, question)
    conversation_id = str(conversation["_id"])
    history = _history(conversation)
    engine = _engine()
    evidence = await _retrieve(engine, question, request)

    async def event_stream():
        yield _sse(
            {
                "type": "meta",
                "question": question,
                "grounded": bool(evidence),
                "evidence": [item.model_dump() for item in evidence],
                "conversation_id": conversation_id,
            }
        )
        if not evidence:
            await _append_turn(
                conversation,
                request,
                question=question,
                answer=MISSING_CONTEXT_MESSAGE,
                grounded=False,
                evidence=[],
            )
            yield _sse(
                {
                    "type": "done",
                    "answer": MISSING_CONTEXT_MESSAGE,
                    "grounded": False,
                    "evidence": [],
                    "conversation_id": conversation_id,
                }
            )
            return

        messages = engine.build_messages(question, evidence, history=history)
        parts: list[str] = []
        try:
            async for token in engine.generate_stream(messages):
                parts.append(token)
                yield _sse({"type": "token", "text": token})
        except OllamaError:
            logger.warning("Streaming generation failed", exc_info=True)
            yield _sse({"type": "error", "detail": LLM_UNAVAILABLE})
            return
        answer = "".join(parts).strip()
        await _append_turn(
            conversation,
            request,
            question=question,
            answer=answer,
            grounded=True,
            evidence=evidence,
        )
        yield _sse(
            {
                "type": "done",
                "answer": answer,
                "grounded": True,
                "evidence": [item.model_dump() for item in evidence],
                "conversation_id": conversation_id,
            }
        )

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
