"""Core RAG: context building, grounded prompting, chat engine."""

from app.rag.context import build_context
from app.rag.engine import ChatEngine
from app.rag.prompts import MISSING_CONTEXT_MESSAGE, SYSTEM_PROMPT, build_messages

__all__ = [
    "MISSING_CONTEXT_MESSAGE",
    "SYSTEM_PROMPT",
    "ChatEngine",
    "build_context",
    "build_messages",
]
