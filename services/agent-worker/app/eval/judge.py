"""LLM-as-judge: rate how well the Portfolio Manager's rationale is grounded in the
analyst evidence. Optional (adds LLM cost); off by default in the runner."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from ..graph.state import GraphState
from ..llm import LLMClient, Usage


class JudgeScore(BaseModel):
    model_config = ConfigDict(extra="forbid")

    score: int = Field(..., ge=1, le=5, description="1=unsupported, 5=fully grounded")
    reason: str


async def judge_rationale(
    state: GraphState, llm: LLMClient
) -> tuple[JudgeScore, Usage]:
    rec = state.get("recommendation")
    summaries = "\n".join(
        f"- {o.agent_type.value}: {o.summary}" for o in state.get("analyst_outputs", [])
    )
    system = (
        "You are an evaluation judge. Rate, from 1 to 5, how well the Portfolio "
        "Manager's rationale is GROUNDED in the analyst findings — not whether you "
        "agree with the call. Penalize claims unsupported by the evidence."
    )
    user = (
        f"Analyst findings:\n{summaries}\n\n"
        f"Decision: {rec.recommendation.value if rec else 'none'}\n"
        f"Rationale: {rec.rationale if rec else ''}\n"
    )
    return await llm.structured(system=system, user=user, schema=JudgeScore)
