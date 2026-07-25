"""Research pipeline queries + command handlers (create request, build views,
recommendations, leaderboard, memory search)."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from aegis_shared.contracts import (
    AgentRunView,
    AgentScorecard,
    AgentType,
    DebateTranscript,
    DebateTurn,
    MemoryHit,
    MemorySearchResponse,
    PerformanceLeaderboard,
    RecommendationView,
    RequestStatus,
    ResearchResultView,
)
from aegis_shared.db import (
    AgentContribution,
    AgentRun,
    Debate,
    Memory,
    Recommendation,
    ResearchRequest,
)

from ..adapters import Queue


class ResearchService:
    def __init__(self, session: AsyncSession, queue: Queue) -> None:
        self._session = session
        self._queue = queue

    # ---- commands -----------------------------------------------------------

    async def create_request(
        self, user_id: UUID, ticker: str, enable_debate: bool, max_debate_rounds: int
    ) -> ResearchRequest:
        request = ResearchRequest(
            user_id=user_id,
            ticker=ticker.upper(),
            status=RequestStatus.QUEUED.value,
            params={
                "enable_debate": enable_debate,
                "max_debate_rounds": max_debate_rounds,
            },
        )
        self._session.add(request)
        await self._session.commit()
        await self._session.refresh(request)

        await self._queue.enqueue(
            {
                "request_id": str(request.id),
                "ticker": request.ticker,
                "enable_debate": enable_debate,
                "max_debate_rounds": max_debate_rounds,
            }
        )
        return request

    # ---- queries ------------------------------------------------------------

    async def get_status(self, request_id: UUID) -> RequestStatus | None:
        req = await self._session.get(ResearchRequest, request_id)
        return RequestStatus(req.status) if req else None

    async def get_result(self, request_id: UUID) -> ResearchResultView | None:
        stmt = (
            select(ResearchRequest)
            .where(ResearchRequest.id == request_id)
            .options(
                selectinload(ResearchRequest.agent_runs).selectinload(AgentRun.output),
                selectinload(ResearchRequest.debate).selectinload(Debate.turns),
                selectinload(ResearchRequest.recommendation),
            )
        )
        req = (await self._session.execute(stmt)).scalar_one_or_none()
        if req is None:
            return None
        return _to_result_view(req)

    async def list_recommendations(
        self, ticker: str | None, limit: int, offset: int
    ) -> list[RecommendationView]:
        stmt = select(Recommendation).order_by(Recommendation.created_at.desc())
        if ticker:
            stmt = stmt.where(Recommendation.ticker == ticker.upper())
        stmt = stmt.limit(limit).offset(offset)
        rows = (await self._session.execute(stmt)).scalars().all()
        return [_to_recommendation_view(r) for r in rows]

    async def agent_leaderboard(self) -> PerformanceLeaderboard:
        rows = (await self._session.execute(select(AgentContribution))).scalars().all()
        return _build_leaderboard(rows)

    async def search_memory(
        self, query: str, ticker: str | None, limit: int
    ) -> MemorySearchResponse:
        # Text search over stored summaries. NOTE: true semantic search runs a
        # pgvector cosine query and belongs in a shared embedding service so the
        # gateway stays free of LLM dependencies; tracked as a follow-up.
        stmt = select(Memory).where(Memory.summary.ilike(f"%{query}%"))
        if ticker:
            stmt = stmt.where(Memory.ticker == ticker.upper())
        stmt = stmt.order_by(Memory.created_at.desc()).limit(limit)
        rows = (await self._session.execute(stmt)).scalars().all()
        hits = [
            MemoryHit(
                memory_id=m.id,
                ticker=m.ticker,
                summary=m.summary,
                created_at=m.created_at,
                similarity=1.0,
            )
            for m in rows
        ]
        return MemorySearchResponse(query=query, hits=hits)


# ---- mapping helpers --------------------------------------------------------

def _to_result_view(req: ResearchRequest) -> ResearchResultView:
    agent_runs = [
        AgentRunView(
            id=run.id,
            agent_type=AgentType(run.agent_type),
            status=run.status,
            confidence=run.output.confidence if run.output else None,
            latency_ms=run.latency_ms,
            tokens_in=run.tokens_in,
            tokens_out=run.tokens_out,
            output=run.output.payload if run.output else None,
        )
        for run in req.agent_runs
    ]

    debate = None
    if req.debate is not None:
        debate = DebateTranscript(
            rounds=req.debate.rounds,
            turns=[
                DebateTurn(
                    round=t.round,
                    agent_type=AgentType(t.agent_type),
                    argument=t.argument,
                    rebuts=AgentType(t.rebuts) if t.rebuts else None,
                )
                for t in req.debate.turns
            ],
        )

    recommendation = (
        _to_recommendation_view(req.recommendation) if req.recommendation else None
    )

    return ResearchResultView(
        request_id=req.id,
        ticker=req.ticker,
        status=RequestStatus(req.status),
        created_at=req.created_at,
        agent_runs=agent_runs,
        debate=debate,
        recommendation=recommendation,
    )


def _to_recommendation_view(rec: Recommendation) -> RecommendationView:
    return RecommendationView(
        id=rec.id,
        ticker=rec.ticker,
        action=rec.action,
        confidence=rec.confidence,
        rationale=rec.rationale,
        key_risks=rec.key_risks,
        supporting_factors=rec.supporting_factors,
        created_at=rec.created_at,
    )


def _build_leaderboard(rows: list[AgentContribution]) -> PerformanceLeaderboard:
    by_agent: dict[str, list[AgentContribution]] = {}
    for r in rows:
        by_agent.setdefault(r.agent_type, []).append(r)

    scorecards: list[AgentScorecard] = []
    for agent_type, contribs in by_agent.items():
        known = [c for c in contribs if c.was_correct is not None]
        accuracy = (
            sum(1 for c in known if c.was_correct) / len(known) if known else 0.0
        )
        avg_conf = sum(c.confidence for c in contribs) / len(contribs)
        scorecards.append(
            AgentScorecard(
                agent_type=AgentType(agent_type),
                total_contributions=len(contribs),
                accuracy=round(accuracy, 4),
                avg_confidence=round(avg_conf, 4),
                calibration_gap=round(avg_conf - accuracy, 4),
            )
        )

    scorecards.sort(key=lambda s: s.accuracy, reverse=True)
    best = scorecards[0].agent_type if scorecards else None
    worst = scorecards[-1].agent_type if scorecards else None
    return PerformanceLeaderboard(
        scorecards=scorecards, best_agent=best, worst_agent=worst
    )
