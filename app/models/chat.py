"""Chat request/response models."""

from __future__ import annotations

from pydantic import BaseModel, Field

from app.models.evidence import Evidence


class ChatRequest(BaseModel):
    question: str = Field(min_length=1, max_length=2000)
    subject: str | None = Field(default=None, min_length=1, max_length=120)
    semester: int | None = Field(default=None, ge=1, le=12)
    document_id: str | None = None
    top_k: int | None = Field(default=None, ge=1, le=50)
    conversation_id: str | None = None


class ChatResponse(BaseModel):
    answer: str
    evidence: list[Evidence]
    grounded: bool
    conversation_id: str
