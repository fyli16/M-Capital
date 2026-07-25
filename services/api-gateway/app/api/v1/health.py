"""Health + Prometheus metrics endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Request, Response

from aegis_shared.contracts import HealthResponse

from ...adapters import InMemoryQueue
from ...core.db import ping as db_ping
from ...core.observability import metrics_response

router = APIRouter(tags=["ops"])


@router.get("/health", response_model=HealthResponse)
async def health(request: Request) -> HealthResponse:
    database = await db_ping()

    redis_ok = False
    redis_client = getattr(request.app.state, "redis", None)
    if redis_client is not None:
        try:
            redis_ok = bool(await redis_client.ping())
        except Exception:
            redis_ok = False

    queue = getattr(request.app.state, "queue", None)
    # In-memory queue is always "up"; a real SQS client is assumed reachable.
    queue_ok = queue is not None

    return HealthResponse(
        status="ok" if database else "degraded",
        database=database,
        redis=redis_ok,
        queue=queue_ok,
    )


@router.get("/metrics")
async def metrics() -> Response:
    return metrics_response()
