"""LangGraph state definition and worker-domain records."""

from __future__ import annotations

import operator
from typing import Annotated, Any, TypedDict

from pydantic import BaseModel

from aegis_shared.contracts import (
    AgentType,
    BaseAgentOutput,
    DebateTurn,
    PortfolioManagerOutput,
    RunStatus,
)


class AgentRunRecord(BaseModel):
    """Per-agent execution telemetry captured during the graph run."""

    agent_type: AgentType
    status: RunStatus
    latency_ms: int | None = None
    tokens_in: int = 0
    tokens_out: int = 0
    cost_usd: float = 0.0
    confidence: float | None = None
    error: str | None = None


class GraphState(TypedDict, total=False):
    """Channels flowing through the graph.

    List channels use ``operator.add`` reducers so the parallel analyst branches can
    append concurrently without clobbering each other. Scalar channels are
    last-value-wins and only ever written by a single node per superstep.
    """

    # inputs
    request_id: str
    ticker: str
    enable_debate: bool
    max_debate_rounds: int

    # gathered context
    tool_context: Any
    memory_hits: list[dict[str, Any]]

    # parallel-accumulated channels
    analyst_outputs: Annotated[list[BaseAgentOutput], operator.add]
    agent_runs: Annotated[list[AgentRunRecord], operator.add]
    debate_turns: Annotated[list[DebateTurn], operator.add]

    # debate / synthesis
    stances: dict[str, float]
    conflict: Any
    debate_round: int
    debate_outcome: str
    recommendation: PortfolioManagerOutput


def make_initial_state(
    ticker: str,
    request_id: str,
    enable_debate: bool,
    max_debate_rounds: int,
) -> GraphState:
    return {
        "request_id": request_id,
        "ticker": ticker.upper(),
        "enable_debate": enable_debate,
        "max_debate_rounds": max_debate_rounds,
        "analyst_outputs": [],
        "agent_runs": [],
        "debate_turns": [],
        "stances": {},
        "debate_round": 0,
    }
