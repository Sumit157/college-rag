"""Retrieval evidence: the data returned by semantic search."""

from __future__ import annotations

from pydantic import BaseModel, Field


class Evidence(BaseModel):
    id: str
    document_id: str
    filename: str
    page: int | None = None
    section: str | None = None
    chunk_id: str
    text: str
    relevance: float = Field(ge=0.0, le=1.0)


class SearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=2000)
    subject: str | None = Field(default=None, min_length=1, max_length=120)
    semester: int | None = Field(default=None, ge=1, le=12)
    document_id: str | None = None
    top_k: int | None = Field(default=None, ge=1, le=50)


class SearchResponse(BaseModel):
    query: str
    evidence: list[Evidence]
    count: int
