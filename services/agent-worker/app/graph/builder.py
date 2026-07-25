"""Assembles the LangGraph workflow.

    START -> data_gather -> [news, financial, quant, macro, risk] (parallel)
          -> assess (fan-in + conflict detection)
          -> {debate loop | synthesize}
          -> synthesize (Portfolio Manager) -> persist -> END
"""

from __future__ import annotations

from typing import Any

from langgraph.graph import END, START, StateGraph

from .deps import Deps
from .nodes import (
    make_analyst_node,
    make_assess_node,
    make_data_gather_node,
    make_debate_node,
    make_persist_node,
    make_route_after_round,
    make_synthesis_node,
    route_after_assess,
)
from .state import GraphState


def build_graph(deps: Deps, checkpointer: Any | None = None):
    g = StateGraph(GraphState)

    g.add_node("data_gather", make_data_gather_node(deps))
    for agent in deps.analysts:
        g.add_node(agent.agent_type.value, make_analyst_node(agent, deps))
    g.add_node("assess", make_assess_node(deps))
    g.add_node("debate", make_debate_node(deps))
    g.add_node("synthesize", make_synthesis_node(deps))
    g.add_node("persist", make_persist_node(deps))

    g.add_edge(START, "data_gather")
    for agent in deps.analysts:
        name = agent.agent_type.value
        g.add_edge("data_gather", name)   # fan-out
        g.add_edge(name, "assess")        # fan-in barrier

    g.add_conditional_edges(
        "assess",
        route_after_assess,
        {"debate": "debate", "synthesize": "synthesize"},
    )
    g.add_conditional_edges(
        "debate",
        make_route_after_round(deps),
        {"debate": "debate", "synthesize": "synthesize"},
    )
    g.add_edge("synthesize", "persist")
    g.add_edge("persist", END)

    return g.compile(checkpointer=checkpointer)
