"""Assembles all tool data for a ticker into a single ``ToolContext``."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Any, Protocol

from ..config import Settings
from .cache import Cache
from .providers import (
    DataProviders,
    FilingsData,
    Fundamentals,
    MarketData,
    NewsData,
)


class MemorySearcher(Protocol):
    async def search(self, query: str, ticker: str, limit: int) -> list[dict[str, Any]]: ...


@dataclass
class ToolContext:
    ticker: str
    market: MarketData
    fundamentals: Fundamentals
    news: NewsData
    filings: FilingsData
    memory_hits: list[dict[str, Any]] = field(default_factory=list)


async def _cached(cache: Cache | None, key: str, ttl: int, fn, *args):
    if cache is not None:
        hit = await cache.get(key)
        if hit is not None:
            return hit
    value = await asyncio.to_thread(fn, *args)
    if cache is not None:
        await cache.set(key, value, ttl)
    return value


async def gather_tool_context(
    ticker: str,
    settings: Settings,
    providers: DataProviders,
    cache: Cache | None = None,
    memory: MemorySearcher | None = None,
) -> ToolContext:
    ttl = settings.tool_cache_ttl_seconds
    market, fundamentals, news, filings = await asyncio.gather(
        _cached(cache, f"market:{ticker}", ttl, providers.market.fetch, ticker),
        _cached(cache, f"fund:{ticker}", ttl, providers.fundamentals.fetch, ticker),
        _cached(cache, f"news:{ticker}", ttl, providers.news.fetch, ticker),
        _cached(cache, f"sec:{ticker}", ttl, providers.filings.fetch, ticker),
    )

    memory_hits: list[dict[str, Any]] = []
    if memory is not None:
        try:
            memory_hits = await memory.search(
                query=f"prior analysis of {ticker}", ticker=ticker, limit=5
            )
        except Exception:  # memory is best-effort; never block analysis
            memory_hits = []

    return ToolContext(
        ticker=ticker,
        market=market,
        fundamentals=fundamentals,
        news=news,
        filings=filings,
        memory_hits=memory_hits,
    )
