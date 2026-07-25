"""Research endpoints: submit analysis, fetch result, stream live progress (SSE)."""

from __future__ import annotations

import asyncio
import json
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import StreamingResponse

from aegis_shared.contracts import (
    CreateResearchRequest,
    RequestStatus,
    ResearchRequestAccepted,
    ResearchResultView,
    UserRole,
)

from ...config import Settings, get_settings
from ...core.rate_limit import RateLimit
from ...core.security import CurrentUser, get_current_user, require_roles
from ...services import ResearchService
from ..deps import get_research_service

router = APIRouter(prefix="/research", tags=["research"])

_TERMINAL = {RequestStatus.COMPLETE, RequestStatus.FAILED}


@router.post(
    "",
    response_model=ResearchRequestAccepted,
    status_code=status.HTTP_202_ACCEPTED,
)
async def submit_research(
    body: CreateResearchRequest,
    user: CurrentUser = Depends(require_roles(UserRole.ANALYST, UserRole.ADMIN)),
    service: ResearchService = Depends(get_research_service),
    _: None = Depends(RateLimit()),
) -> ResearchRequestAccepted:
    request = await service.create_request(
        user_id=user.id,
        ticker=body.ticker,
        enable_debate=body.enable_debate,
        max_debate_rounds=body.max_debate_rounds,
    )
    return ResearchRequestAccepted(
        request_id=request.id,
        status=RequestStatus.QUEUED,
        stream_url=f"/api/v1/research/{request.id}/stream",
    )


@router.get("/{request_id}", response_model=ResearchResultView)
async def get_research(
    request_id: UUID,
    _user: CurrentUser = Depends(get_current_user),
    service: ResearchService = Depends(get_research_service),
) -> ResearchResultView:
    result = await service.get_result(request_id)
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Research request not found"
        )
    return result


def _sse(event: str, data: str) -> bytes:
    return f"event: {event}\ndata: {data}\n\n".encode()


@router.get("/{request_id}/stream")
async def stream_research(
    request_id: UUID,
    service: ResearchService = Depends(get_research_service),
    settings: Settings = Depends(get_settings),
) -> StreamingResponse:
    """Server-Sent Events: emit status transitions, then the final result.

    Polls the database (a Redis pub/sub fast-path from the worker is the planned
    low-latency upgrade). Bounded by ``sse_max_seconds``.
    """

    async def generator():
        last_status: RequestStatus | None = None
        iterations = int(settings.sse_max_seconds / settings.sse_poll_interval_seconds)
        for _ in range(max(1, iterations)):
            current = await service.get_status(request_id)
            if current is None:
                yield _sse("error", json.dumps({"detail": "not found"}))
                return
            if current != last_status:
                yield _sse("status", json.dumps({"status": current.value}))
                last_status = current
            if current in _TERMINAL:
                result = await service.get_result(request_id)
                payload = result.model_dump(mode="json") if result else {}
                yield _sse("complete", json.dumps(payload))
                return
            await asyncio.sleep(settings.sse_poll_interval_seconds)
        yield _sse("timeout", json.dumps({"detail": "stream timed out"}))

    return StreamingResponse(generator(), media_type="text/event-stream")
