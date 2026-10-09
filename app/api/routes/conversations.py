"""Conversation endpoints: chat history list, detail, delete."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from fastapi.concurrency import run_in_threadpool

from app.database.mongo import get_mongo
from app.database.repositories import ConversationRepository
from app.models.conversation import (
    ConversationDetail,
    ConversationListResponse,
    ConversationSummary,
    DeleteConversationResponse,
    conversation_to_detail,
    conversation_to_summary,
)

router = APIRouter(prefix="/conversations", tags=["conversations"])

NOT_FOUND = "Conversation not found."


def _repo() -> ConversationRepository:
    return ConversationRepository(get_mongo().db)


def ensure_indexes() -> None:
    _repo().ensure_indexes()


@router.get("", response_model=ConversationListResponse)
async def list_conversations() -> ConversationListResponse:
    docs = await run_in_threadpool(_repo().list)
    return ConversationListResponse(items=[conversation_to_summary(doc) for doc in docs])


@router.get("/{conversation_id}", response_model=ConversationDetail)
async def get_conversation(conversation_id: str) -> ConversationDetail:
    doc = await run_in_threadpool(_repo().get, conversation_id)
    if doc is None:
        raise HTTPException(status_code=404, detail=NOT_FOUND)
    return conversation_to_detail(doc)


@router.delete("/{conversation_id}", response_model=DeleteConversationResponse)
async def delete_conversation(conversation_id: str) -> DeleteConversationResponse:
    deleted = await run_in_threadpool(_repo().delete, conversation_id)
    if not deleted:
        raise HTTPException(status_code=404, detail=NOT_FOUND)
    return DeleteConversationResponse(deleted=conversation_id)
