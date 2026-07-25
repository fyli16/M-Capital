"""Memory search endpoint."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from aegis_shared.contracts import MemorySearchResponse
from aegis_shared.contracts.api import TICKER_PATTERN

from ...core.security import CurrentUser, get_current_user
from ...services import ResearchService
from ..deps import get_research_service

router = APIRouter(prefix="/memory", tags=["memory"])


@router.get("/search", response_model=MemorySearchResponse)
async def search_memory(
    query: str = Query(..., min_length=3),
    ticker: str | None = Query(default=None, pattern=TICKER_PATTERN),
    limit: int = Query(default=10, ge=1, le=50),
    _user: CurrentUser = Depends(get_current_user),
    service: ResearchService = Depends(get_research_service),
) -> MemorySearchResponse:
    return await service.search_memory(query, ticker, limit)
