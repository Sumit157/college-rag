"""Chat endpoints: grounded Q&A over uploaded documents (JSON + streaming)."""

from __future__ import annotations

import json
import logging

from fastapi import APIRouter, HTTPException
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import StreamingResponse

from app.core.config import get_settings
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


@router.post("", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    question = _validate(request.question)
    engine = _engine()
    evidence = await _retrieve(engine, question, request)
    if not evidence:
        return ChatResponse(answer=MISSING_CONTEXT_MESSAGE, evidence=[], grounded=False)

    messages = engine.build_messages(question, evidence)
    try:
        answer = await engine.generate(messages)
    except OllamaError:
        raise HTTPException(status_code=503, detail=LLM_UNAVAILABLE) from None
    if not answer:
        raise HTTPException(status_code=503, detail=LLM_UNAVAILABLE)
    return ChatResponse(answer=answer, evidence=evidence, grounded=True)


def _sse(payload: dict) -> str:
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"


@router.post("/stream")
async def chat_stream(request: ChatRequest) -> StreamingResponse:
    question = _validate(request.question)
    engine = _engine()
    evidence = await _retrieve(engine, question, request)

    async def event_stream():
        yield _sse(
            {
                "type": "meta",
                "question": question,
                "grounded": bool(evidence),
                "evidence": [item.model_dump() for item in evidence],
            }
        )
        if not evidence:
            yield _sse(
                {
                    "type": "done",
                    "answer": MISSING_CONTEXT_MESSAGE,
                    "grounded": False,
                    "evidence": [],
                }
            )
            return

        messages = engine.build_messages(question, evidence)
        parts: list[str] = []
        try:
            async for token in engine.generate_stream(messages):
                parts.append(token)
                yield _sse({"type": "token", "text": token})
        except OllamaError:
            logger.warning("Streaming generation failed", exc_info=True)
            yield _sse({"type": "error", "detail": LLM_UNAVAILABLE})
            return
        yield _sse(
            {
                "type": "done",
                "answer": "".join(parts).strip(),
                "grounded": True,
                "evidence": [item.model_dump() for item in evidence],
            }
        )

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
