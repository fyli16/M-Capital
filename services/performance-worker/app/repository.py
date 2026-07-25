"""Persistence for performance measurement (protocol + SQLAlchemy implementation).

The protocol lets the runner be tested against an in-memory fake, while the SQL
implementation does the real work: find due recommendations, upsert one
``performance_tracking`` row each, and backfill ``agent_contributions.was_correct``.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Protocol
from uuid import UUID

from sqlalchemy import create_engine, or_, select
from sqlalchemy.orm import Session, selectinload, sessionmaker

from aegis_shared.contracts import RecommendationAction
from aegis_shared.db import AgentContribution, PerformanceTracking, Recommendation

from .domain import ContributionRef, DueRecommendation, PerfResult


class PerformanceRepo(Protocol):
    def due_recommendations(
        self, now: datetime, min_age_days: int, limit: int
    ) -> list[DueRecommendation]: ...

    def record_result(
        self, rec_id: UUID, result: PerfResult, correctness: dict[str, bool]
    ) -> None: ...


class SqlPerformanceRepo:
    def __init__(self, database_url: str) -> None:
        self._engine = create_engine(database_url, pool_pre_ping=True)
        self._session: sessionmaker[Session] = sessionmaker(
            bind=self._engine, expire_on_commit=False
        )

    def due_recommendations(
        self, now: datetime, min_age_days: int, limit: int
    ) -> list[DueRecommendation]:
        cutoff = now - timedelta(days=min_age_days)
        stmt = (
            select(Recommendation)
            .outerjoin(
                PerformanceTracking,
                PerformanceTracking.recommendation_id == Recommendation.id,
            )
            .where(Recommendation.created_at <= cutoff)
            .where(
                or_(
                    PerformanceTracking.id.is_(None),
                    PerformanceTracking.ret_90d.is_(None),
                )
            )
            .options(selectinload(Recommendation.contributions))
            .order_by(Recommendation.created_at.asc())
            .limit(limit)
        )
        with self._session() as s:
            rows = s.execute(stmt).scalars().unique().all()
            return [
                DueRecommendation(
                    id=r.id,
                    ticker=r.ticker,
                    action=RecommendationAction(r.action),
                    created_at=r.created_at,
                    contributions=[
                        ContributionRef(agent_type=c.agent_type, supported=c.supported)
                        for c in r.contributions
                    ],
                )
                for r in rows
            ]

    def record_result(
        self, rec_id: UUID, result: PerfResult, correctness: dict[str, bool]
    ) -> None:
        with self._session() as s:
            tracking = (
                s.execute(
                    select(PerformanceTracking).where(
                        PerformanceTracking.recommendation_id == rec_id
                    )
                )
                .scalars()
                .first()
            )
            if tracking is None:
                tracking = PerformanceTracking(recommendation_id=rec_id)
                s.add(tracking)

            tracking.ret_30d = result.ret_30d
            tracking.ret_60d = result.ret_60d
            tracking.ret_90d = result.ret_90d
            tracking.benchmark_ret_90d = result.benchmark_ret_90d
            tracking.measured_at = result.measured_at

            if correctness:
                contribs = (
                    s.execute(
                        select(AgentContribution).where(
                            AgentContribution.recommendation_id == rec_id
                        )
                    )
                    .scalars()
                    .all()
                )
                for c in contribs:
                    if c.agent_type in correctness:
                        c.was_correct = correctness[c.agent_type]

            s.commit()
