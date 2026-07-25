"""Rate limiting with pluggable backends (in-memory default, Redis for the fleet)."""

from __future__ import annotations

import time
from collections import defaultdict, deque

from fastapi import Depends, HTTPException, Request, status

from ..config import Settings, get_settings


class InMemoryRateLimiter:
    """Sliding-window limiter. Single-process only — fine for dev/tests."""

    def __init__(self) -> None:
        self._hits: dict[str, deque[float]] = defaultdict(deque)

    async def allow(self, key: str, limit: int, window: int) -> bool:
        now = time.monotonic()
        bucket = self._hits[key]
        cutoff = now - window
        while bucket and bucket[0] < cutoff:
            bucket.popleft()
        if len(bucket) >= limit:
            return False
        bucket.append(now)
        return True


class RedisRateLimiter:
    """Fixed-window limiter shared across instances (INCR + EXPIRE)."""

    def __init__(self, client) -> None:
        self._client = client

    async def allow(self, key: str, limit: int, window: int) -> bool:
        bucket = f"rl:{key}:{int(time.time()) // window}"
        count = await self._client.incr(bucket)
        if count == 1:
            await self._client.expire(bucket, window)
        return count <= limit


def _limiter(request: Request):
    limiter = getattr(request.app.state, "rate_limiter", None)
    if limiter is None:
        limiter = InMemoryRateLimiter()
        request.app.state.rate_limiter = limiter
    return limiter


def _client_key(request: Request) -> str:
    # Prefer authenticated identity (set by get_current_user); fall back to IP.
    user_id = getattr(request.state, "user_id", None)
    if user_id:
        return f"user:{user_id}"
    client = request.client.host if request.client else "unknown"
    return f"ip:{client}"


class RateLimit:
    """Reusable dependency: ``Depends(RateLimit())`` or with custom limits."""

    def __init__(self, requests: int | None = None, window: int | None = None) -> None:
        self._requests = requests
        self._window = window

    async def __call__(
        self, request: Request, settings: Settings = Depends(get_settings)
    ) -> None:
        limit = self._requests or settings.rate_limit_requests
        window = self._window or settings.rate_limit_window_seconds
        limiter = _limiter(request)
        allowed = await limiter.allow(_client_key(request), limit, window)
        if not allowed:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit exceeded",
                headers={"Retry-After": str(window)},
            )
