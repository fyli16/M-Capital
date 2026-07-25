"""End-to-end analysis runner. The single entry point used by the CLI, the SQS
consumer, and the test-suite."""

from __future__ import annotations

from time import perf_counter
from uuid import uuid4

from .config import Settings, get_settings
from .graph import Deps, build_deps, build_graph, make_initial_state
from .graph.state import GraphState

# Loops (debate self-edge) count against LangGraph's recursion limit; keep headroom.
_RECURSION_LIMIT = 50


async def run_analysis(
    ticker: str,
    *,
    deps: Deps | None = None,
    request_id: str | None = None,
    enable_debate: bool = True,
    max_debate_rounds: int | None = None,
    settings: Settings | None = None,
) -> GraphState:
    settings = settings or get_settings()
    deps = deps or build_deps(settings)
    graph = build_graph(deps)

    rounds = (
        max_debate_rounds
        if max_debate_rounds is not None
        else settings.default_max_rounds
    )
    request_id = request_id or str(uuid4())
    state = make_initial_state(
        ticker=ticker,
        request_id=request_id,
        enable_debate=enable_debate,
        max_debate_rounds=rounds,
    )

    telemetry = deps.telemetry
    started = perf_counter()
    try:
        with telemetry.workflow_span(ticker=state["ticker"], request_id=request_id):
            final = await graph.ainvoke(
                state, config={"recursion_limit": _RECURSION_LIMIT}
            )
    except Exception:
        telemetry.record_workflow(
            ticker=state["ticker"],
            outcome="error",
            duration_ms=(perf_counter() - started) * 1000,
            failed=True,
            num_agents=0,
            debate_rounds=0,
        )
        raise

    telemetry.record_workflow(
        ticker=state["ticker"],
        outcome=final.get("debate_outcome") or "complete",
        duration_ms=(perf_counter() - started) * 1000,
        failed=False,
        num_agents=len(final.get("agent_runs", [])),
        debate_rounds=final.get("debate_round", 0),
    )
    return final
