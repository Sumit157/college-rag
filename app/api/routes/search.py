"""Semantic search endpoint: question → evidence."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.core.config import get_settings
from app.embeddings.errors import EmbeddingError
from app.embeddings.provider import get_embedding_provider
from app.models.evidence import SearchRequest, SearchResponse
from app.retrieval.retriever import Retriever
from app.retrieval.vector_store import RetrievalError, get_vector_store

router = APIRouter(tags=["search"])


@router.post("/search", response_model=SearchResponse)
def search(request: SearchRequest) -> SearchResponse:
    query = request.query.strip()
    if not query:
        raise HTTPException(status_code=422, detail="The search query must not be empty.")

    settings = get_settings()
    retriever = Retriever(
        embeddings=get_embedding_provider(),
        store=get_vector_store(),
        default_top_k=settings.retrieval_top_k,
    )
    try:
        evidence = retriever.retrieve(
            query=query,
            subject=request.subject,
            semester=request.semester,
            document_id=request.document_id,
            top_k=request.top_k,
        )
    except EmbeddingError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from None
    except RetrievalError as exc:
        raise HTTPException(status_code=503, detail=exc.message) from None

    return SearchResponse(query=query, evidence=evidence, count=len(evidence))
