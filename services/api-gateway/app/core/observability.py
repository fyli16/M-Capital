"""Prometheus metrics + audit-logging middleware."""

from __future__ import annotations

import json
import logging
import time

from fastapi import Request, Response
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger("aegis.gateway.audit")

REQUESTS = Counter(
    "aegis_http_requests_total",
    "HTTP requests",
    ["method", "path", "status"],
)
LATENCY = Histogram(
    "aegis_http_request_duration_seconds",
    "HTTP request latency",
    ["method", "path"],
)


def _route(request: Request) -> str:
    """Use the route template (not the raw path) to keep label cardinality bounded."""
    route = request.scope.get("route")
    return getattr(route, "path", request.url.path)


class ObservabilityMiddleware(BaseHTTPMiddleware):
    """Records request metrics and writes a structured audit log line per request."""

    async def dispatch(self, request: Request, call_next):
        start = time.perf_counter()
        try:
            response = await call_next(request)
            status_code = response.status_code
        except Exception:
            status_code = 500
            self._emit(request, status_code, start)
            raise

        path = _route(request)
        elapsed = time.perf_counter() - start
        REQUESTS.labels(request.method, path, str(status_code)).inc()
        LATENCY.labels(request.method, path).observe(elapsed)
        self._emit(request, status_code, start)
        return response

    @staticmethod
    def _emit(request: Request, status_code: int, start: float) -> None:
        logger.info(
            json.dumps(
                {
                    "event": "http_request",
                    "method": request.method,
                    "path": request.url.path,
                    "status": status_code,
                    "duration_ms": round((time.perf_counter() - start) * 1000, 2),
                    "user_id": getattr(request.state, "user_id", None),
                    "client": request.client.host if request.client else None,
                }
            )
        )


def metrics_response() -> Response:
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
