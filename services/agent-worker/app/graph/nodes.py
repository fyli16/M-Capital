"""Graph node factories.

Each factory captures ``Deps`` in a closure and returns an async node function.
Nodes return **partial** state updates; reducers merge parallel writes.
"""

from __future__ import annotations

import asyncio
from time import perf_counter
from typing import Callable

from aegis_shared.contracts import AgentType, DebateOutcome, RunStatus

from ..agents import AnalystAgent
from ..agents.portfolio_manager import aggregate
from ..debate import detect_conflict, run_debate_round
from ..tools import gather_tool_context
from .deps import Deps
from .state import AgentRunRecord, GraphState


def make_data_gather_node(deps: Deps) -> Callable:
    async def data_gather(state: GraphState) -> dict:
        with deps.telemetry.node_span("data_gather", ticker=state["ticker"]):
            ctx = await gather_tool_context(
                state["ticker"], deps.settings, deps.providers, deps.cache, deps.memory
            )
        return {"tool_context": ctx, "memory_hits": ctx.memory_hits}

    return data_gather


def make_analyst_node(agent: AnalystAgent, deps: Deps) -> Callable:
    async def node(state: GraphState) -> dict:
        ctx = state["tool_context"]
        tel = deps.telemetry
        with tel.node_span(
            f"agent.{agent.agent_type.value}",
            agent_type=agent.agent_type.value,
            ticker=state["ticker"],
        ):
            t0 = perf_counter()
            try:
                out, usage = await asyncio.wait_for(
                    agent.analyze(ctx, deps.llm),
                    timeout=deps.settings.agent_timeout_seconds,
                )
            except Exception as exc:  # timeout / invalid output -> abstain, don't fail run
                rec = AgentRunRecord(
                    agent_type=agent.agent_type,
                    status=RunStatus.ABSTAINED,
                    latency_ms=int((perf_counter() - t0) * 1000),
                    error=str(exc)[:500],
                )
                tel.record_agent_run(rec)
                return {"agent_runs": [rec]}

            rec = AgentRunRecord(
                agent_type=agent.agent_type,
                status=RunStatus.COMPLETE,
                latency_ms=int((perf_counter() - t0) * 1000),
                tokens_in=usage.tokens_in,
                tokens_out=usage.tokens_out,
                cost_usd=usage.cost_usd,
                confidence=out.confidence,
            )
            tel.record_agent_run(rec)
            return {"analyst_outputs": [out], "agent_runs": [rec]}

    return node


def make_assess_node(deps: Deps) -> Callable:
    async def assess(state: GraphState) -> dict:
        report = detect_conflict(
            state["analyst_outputs"], deps.settings.conflict_threshold
        )
        return {"stances": report.stances, "conflict": report}

    return assess


def route_after_assess(state: GraphState) -> str:
    conflict = state.get("conflict")
    if (
        state.get("enable_debate", True)
        and conflict is not None
        and conflict.has_conflict
        and state.get("max_debate_rounds", 0) > 0
    ):
        return "debate"
    return "synthesize"


def make_debate_node(deps: Deps) -> Callable:
    async def debate(state: GraphState) -> dict:
        round_no = state.get("debate_round", 0) + 1
        with deps.telemetry.node_span("debate.round", round=round_no):
            result = await run_debate_round(
                round_no,
                state["stances"],
                state["analyst_outputs"],
                deps.llm,
                deps.settings.debate_damping,
            )
        return {
            "debate_turns": result.turns,
            "stances": result.stances,
            "debate_round": result.round,
        }

    return debate


def make_route_after_round(deps: Deps) -> Callable:
    def route(state: GraphState) -> str:
        values = list(state["stances"].values())
        spread = (max(values) - min(values)) if values else 0.0
        converged = spread <= deps.settings.converge_threshold
        at_cap = state["debate_round"] >= state["max_debate_rounds"]
        return "synthesize" if (converged or at_cap) else "debate"

    return route


def _debate_outcome(state: GraphState, deps: Deps) -> str:
    if not state.get("debate_turns"):
        return DebateOutcome.NO_CONFLICT.value
    values = list(state["stances"].values())
    spread = (max(values) - min(values)) if values else 0.0
    if spread <= 0.05:
        return DebateOutcome.CONSENSUS.value
    if spread <= deps.settings.converge_threshold:
        return DebateOutcome.CONVERGED.value
    return DebateOutcome.MAX_ROUNDS.value


def make_synthesis_node(deps: Deps) -> Callable:
    async def synthesize(state: GraphState) -> dict:
        outputs = state["analyst_outputs"]
        stances = state["stances"]
        with deps.telemetry.node_span(
            "agent.portfolio_manager", ticker=state["ticker"]
        ):
            action, confidence, score = aggregate(outputs, stances)
            decision, usage = await deps.pm.narrate(
                state["ticker"],
                outputs,
                state.get("debate_turns", []),
                action,
                confidence,
                score,
                deps.llm,
            )
        run = AgentRunRecord(
            agent_type=AgentType.PORTFOLIO_MANAGER,
            status=RunStatus.COMPLETE,
            tokens_in=usage.tokens_in,
            tokens_out=usage.tokens_out,
            cost_usd=usage.cost_usd,
            confidence=decision.confidence,
        )
        deps.telemetry.record_agent_run(run)
        return {
            "recommendation": decision,
            "agent_runs": [run],
            "debate_outcome": _debate_outcome(state, deps),
        }

    return synthesize


def make_persist_node(deps: Deps) -> Callable:
    async def persist(state: GraphState) -> dict:
        if deps.persistence is not None:
            try:
                await deps.persistence(state)
            except Exception:  # persistence must never break the run result
                pass
        if deps.memory is not None and state.get("recommendation") is not None:
            rec = state["recommendation"]
            try:
                await deps.memory.remember(
                    ticker=state["ticker"],
                    summary=rec.rationale[:400],
                    content={
                        "recommendation": rec.recommendation.value,
                        "confidence": rec.confidence,
                    },
                    request_id=state.get("request_id"),
                )
            except Exception:
                pass
        return {}

    return persist
