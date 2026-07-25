"""Tiny async cache abstraction.

Deterministic tool results are cacheable by ``(tool, ticker)``. The default is an
in-process TTL cache; a Redis-backed implementation with the same ``get``/``set``
signature slots in for the distributed deployment (workers share the cache).
"""

from __future__ import annotations

import time
from typing import Any, Protocol


class Cache(Protocol):
    async def get(self, key: str) -> Any | None: ...
    async def set(self, key: str, value: Any, ttl: int) -> None: ...


class InMemoryTTLCache:
    def __init__(self) -> None:
        self._store: dict[str, tuple[float, Any]] = {}

    async def get(self, key: str) -> Any | None:
        item = self._store.get(key)
        if item is None:
            return None
        expires_at, value = item
        if expires_at < time.monotonic():
            self._store.pop(key, None)
            return None
        return value

    async def set(self, key: str, value: Any, ttl: int) -> None:
        self._store[key] = (time.monotonic() + ttl, value)
