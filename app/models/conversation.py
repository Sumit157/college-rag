"""Conversation (chat history) API schemas."""

from __future__ import annotations

from datetime import datetime, timezone

from pydantic import BaseModel

from app.models.evidence import Evidence


class ConversationTurn(BaseModel):
    id: str
    question: str
    answer: str
    grounded: bool
    evidence: list[Evidence]
    subject: str | None = None
    semester: int | None = None
    document_id: str | None = None
    created_at: datetime


class ConversationSummary(BaseModel):
    id: str
    title: str
    turn_count: int
    created_at: datetime
    updated_at: datetime


class ConversationDetail(BaseModel):
    id: str
    title: str
    turn_count: int
    turns: list[ConversationTurn]
    created_at: datetime
    updated_at: datetime


class ConversationListResponse(BaseModel):
    items: list[ConversationSummary]


class DeleteConversationResponse(BaseModel):
    deleted: str


def conversation_to_summary(doc: dict) -> ConversationSummary:
    return ConversationSummary(
        id=str(doc["_id"]),
        title=doc.get("title", ""),
        turn_count=int(doc.get("turn_count", 0)),
        created_at=doc.get("created_at") or datetime.now(timezone.utc),
        updated_at=doc.get("updated_at") or datetime.now(timezone.utc),
    )


def conversation_to_detail(doc: dict) -> ConversationDetail:
    turns = [
        ConversationTurn(
            id=turn.get("id", f"turn-{index}"),
            question=turn.get("question", ""),
            answer=turn.get("answer", ""),
            grounded=bool(turn.get("grounded", False)),
            evidence=[Evidence.model_validate(item) for item in turn.get("evidence", [])],
            subject=turn.get("subject"),
            semester=turn.get("semester"),
            document_id=turn.get("document_id"),
            created_at=turn.get("created_at") or datetime.now(timezone.utc),
        )
        for index, turn in enumerate(doc.get("turns", []), start=1)
    ]
    return ConversationDetail(
        id=str(doc["_id"]),
        title=doc.get("title", ""),
        turn_count=int(doc.get("turn_count", 0)),
        turns=turns,
        created_at=doc.get("created_at") or datetime.now(timezone.utc),
        updated_at=doc.get("updated_at") or datetime.now(timezone.utc),
    )
