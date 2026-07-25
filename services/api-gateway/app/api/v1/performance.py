"""Agent performance leaderboard."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from aegis_shared.contracts import PerformanceLeaderboard

from ...core.security import CurrentUser, get_current_user
from ...services import ResearchService
from ..deps import get_research_service

router = APIRouter(prefix="/agent-performance", tags=["performance"])


@router.get("", response_model=PerformanceLeaderboard)
async def agent_performance(
    _user: CurrentUser = Depends(get_current_user),
    service: ResearchService = Depends(get_research_service),
) -> PerformanceLeaderboard:
    return await service.agent_leaderboard()
