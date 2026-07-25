"""pgvector-backed episodic memory: retrieve prior analyses, write new ones back.

Retrieval uses cosine distance against the HNSW index defined in the migration.
All DB work runs in a worker thread so it never blocks the async event loop.
"""

from __future__ import annotations

import asyncio
from typing import Any

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from aegis_shared.db import Embedding, Memory

from ..llm import LLMClient


class MemoryStore:
    def __init__(self, database_url: str, embedder: LLMClient, model: str) -> None:
        # future_engine + pool_pre_ping keeps long-lived workers resilient to
        # dropped connections; PgBouncer sits in front in production.
        self._engine = create_engine(database_url, pool_pre_ping=True)
        self._session: sessionmaker[Session] = sessionmaker(
            bind=self._engine, expire_on_commit=False
        )
        self._embedder = embedder
        self._model = model

    async def search(
        self, query: str, ticker: str, limit: int = 5
    ) -> list[dict[str, Any]]:
        vec, _ = await self._embedder.embed(query)
        return await asyncio.to_thread(self._search_sync, vec, ticker, limit)

    def _search_sync(
        self, vec: list[float], ticker: str, limit: int
    ) -> list[dict[str, Any]]:
        distance = Embedding.embedding.cosine_distance(vec).label("distance")
        stmt = (
            select(Memory, distance)
            .join(Embedding, Embedding.memory_id == Memory.id)
            .where(Memory.ticker == ticker)
            .order_by(distance)
            .limit(limit)
        )
        with self._session() as s:
            rows = s.execute(stmt).all()
        return [
            {
                "memory_id": str(mem.id),
                "ticker": mem.ticker,
                "summary": mem.summary,
                "created_at": mem.created_at.isoformat(),
                "similarity": round(1.0 - float(dist), 4),
            }
            for mem, dist in rows
        ]

    async def remember(
        self,
        ticker: str,
        summary: str,
        content: dict[str, Any],
        request_id: str | None = None,
    ) -> str:
        vec, _ = await self._embedder.embed(summary)
        return await asyncio.to_thread(
            self._remember_sync, ticker, summary, content, request_id, vec
        )

    def _remember_sync(
        self,
        ticker: str,
        summary: str,
        content: dict[str, Any],
        request_id: str | None,
        vec: list[float],
    ) -> str:
        with self._session() as s:
            mem = Memory(
                ticker=ticker,
                summary=summary,
                content=content,
                request_id=request_id,
            )
            s.add(mem)
            s.flush()
            s.add(Embedding(memory_id=mem.id, model=self._model, embedding=vec))
            s.commit()
            return str(mem.id)
