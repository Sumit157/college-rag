"""Library statistics for the dashboard."""

from __future__ import annotations

from fastapi import APIRouter

from app.api.routes.documents import _documents_repo
from app.models.document import StatsResponse

router = APIRouter(tags=["stats"])


@router.get("/stats", response_model=StatsResponse)
def get_stats() -> StatsResponse:
    stats = _documents_repo().stats()
    return StatsResponse(**stats)
