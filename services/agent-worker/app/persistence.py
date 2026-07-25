"""Persists a completed graph run to Postgres (best-effort, never blocks results).

Assumes the ``research_requests`` row was created by the api-gateway when the job was
enqueued; the worker fills in children (runs, outputs, debate, recommendation,
contributions) and flips the request to ``complete``.
"""

from __future__ import annotations

import asyncio
from uuid import UUID

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from aegis_shared.contracts import RecommendationAction, RequestStatus
from aegis_shared.db import (
    AgentContribution,
    AgentOutput,
    AgentRun,
    Debate,
    DebateTurn,
    Recommendation,
    ResearchRequest,
)

from .debate.conflict import stance_of
from .graph.state import GraphState

_ACTION_SCORE = {
    RecommendationAction.STRONG_BUY: 1.0,
    RecommendationAction.BUY: 0.75,
    RecommendationAction.HOLD: 0.5,
    RecommendationAction.SELL: 0.25,
    RecommendationAction.STRONG_SELL: 0.0,
}


class DbPersistence:
    def __init__(self, database_url: str) -> None:
        self._engine = create_engine(database_url, pool_pre_ping=True)
        self._session: sessionmaker[Session] = sessionmaker(
            bind=self._engine, expire_on_commit=False
        )

    async def __call__(self, state: GraphState) -> None:
        await asyncio.to_thread(self._persist_sync, state)

    def _persist_sync(self, state: GraphState) -> None:
        request_id = state.get("request_id")
        if not request_id:
            return
        with self._session() as s:
            req = s.get(ResearchRequest, UUID(request_id))
            if req is None:
                return  # api-gateway owns creation; nothing to attach to

            outputs_by_agent = {
                o.agent_type.value: o for o in state.get("analyst_outputs", [])
            }
            for record in state.get("agent_runs", []):
                run = AgentRun(
                    request_id=req.id,
                    agent_type=record.agent_type.value,
                    status=record.status.value,
                    tokens_in=record.tokens_in,
                    tokens_out=record.tokens_out,
                    latency_ms=record.latency_ms,
                    cost_usd=record.cost_usd,
                    error=record.error,
                )
                s.add(run)
                s.flush()
                out = outputs_by_agent.get(record.agent_type.value)
                if out is not None:
                    s.add(
                        AgentOutput(
                            run_id=run.id,
                            payload=out.model_dump(mode="json"),
                            confidence=out.confidence,
                            sources=[e.model_dump(mode="json") for e in out.sources],
                        )
                    )

            turns = state.get("debate_turns", [])
            if turns:
                debate = Debate(
                    request_id=req.id,
                    rounds=state.get("debate_round", 0),
                    outcome=state.get("debate_outcome", "no_conflict"),
                )
                s.add(debate)
                s.flush()
                for t in turns:
                    s.add(
                        DebateTurn(
                            debate_id=debate.id,
                            round=t.round,
                            agent_type=t.agent_type.value,
                            argument=t.argument,
                            rebuts=t.rebuts.value if t.rebuts else None,
                        )
                    )

            rec = state.get("recommendation")
            if rec is not None:
                recommendation = Recommendation(
                    request_id=req.id,
                    ticker=state["ticker"],
                    action=rec.recommendation.value,
                    confidence=rec.confidence,
                    rationale=rec.rationale,
                    key_risks=rec.key_risks,
                    supporting_factors=rec.supporting_factors,
                )
                s.add(recommendation)
                s.flush()
                self._attach_contributions(s, recommendation.id, state, rec.recommendation)

            req.status = RequestStatus.COMPLETE.value
            s.commit()

    @staticmethod
    def _attach_contributions(s, rec_id, state, action) -> None:
        action_score = _ACTION_SCORE.get(action, 0.5)
        stances = state.get("stances", {})
        for out in state.get("analyst_outputs", []):
            stance = stances.get(out.agent_type.value, stance_of(out))
            supported = abs(stance - action_score) <= 0.35
            s.add(
                AgentContribution(
                    recommendation_id=rec_id,
                    agent_type=out.agent_type.value,
                    confidence=out.confidence,
                    supported=supported,
                    was_correct=None,  # filled later by performance-worker
                )
            )
