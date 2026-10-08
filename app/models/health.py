"""Shared API response schemas."""

from __future__ import annotations

from pydantic import BaseModel


class MongoHealth(BaseModel):
    status: str
    database: str


class OllamaHealth(BaseModel):
    status: str
    url: str
    models: list[str] = []
    llm_model: str | None = None
    embedding_model: str | None = None
    configured_model_available: bool = False


class HealthResponse(BaseModel):
    status: str
    app: str
    mongo: MongoHealth
    ollama: OllamaHealth
