"""Recommendation listing."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from aegis_shared.contracts import RecommendationView
from aegis_shared.contracts.api import TICKER_PATTERN

from ...core.security import CurrentUser, get_current_user
from ...services import ResearchService
from ..deps import get_research_service

router = APIRouter(prefix="/recommendations", tags=["recommendations"])


@router.get("", response_model=list[RecommendationView])
async def list_recommendations(
    ticker: str | None = Query(default=None, pattern=TICKER_PATTERN),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    _user: CurrentUser = Depends(get_current_user),
    service: ResearchService = Depends(get_research_service),
) -> list[RecommendationView]:
    return await service.list_recommendations(ticker, limit, offset)
