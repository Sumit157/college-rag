"""Health endpoints: MongoDB connectivity and Ollama health check."""

from __future__ import annotations

from fastapi import APIRouter

from app.core.config import get_settings
from app.database.mongo import get_mongo
from app.llm.ollama import OllamaProvider
from app.models.health import HealthResponse, MongoHealth, OllamaHealth

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    settings = get_settings()

    mongo = get_mongo()
    mongo_ok = await _ping_mongo(mongo)
    mongo_health = MongoHealth(
        status="ok" if mongo_ok else "unavailable",
        database=settings.mongodb_database,
    )

    ollama_report = await OllamaProvider().health()
    ollama_health = OllamaHealth(**ollama_report)

    status = "ok" if mongo_ok and ollama_health.status == "ok" else "degraded"
    return HealthResponse(
        status=status,
        app=settings.app_name,
        mongo=mongo_health,
        ollama=ollama_health,
    )


async def _ping_mongo(mongo) -> bool:
    """Run the blocking ping off the event loop."""
    from fastapi.concurrency import run_in_threadpool

    return await run_in_threadpool(mongo.ping)
