"""Runs a single bounded debate round.

Model of persuasion (deliberately simple and auditable): each round the current
bull champion and bear champion exchange rebuttals (text authored by the LLM), then
both stances are **damped toward the group mean**. Spread shrinks monotonically, so
the debate provably converges; the orchestrator stops once spread ≤ threshold or the
round cap is hit.

Limitation / future work: a richer version would re-invoke the champions to
*re-score* their conviction after hearing the rebuttal, rather than applying a fixed
damping factor. That costs more tokens; damping is the bounded v1.
"""

from __future__ import annotations

from statistics import mean

from pydantic import BaseModel, ConfigDict

from aegis_shared.contracts import AgentType, BaseAgentOutput, DebateTurn

from ..llm import LLMClient, Usage


class ArgumentText(BaseModel):
    model_config = ConfigDict(extra="forbid")

    argument: str


class RoundResult(BaseModel):
    round: int
    turns: list[DebateTurn]
    stances: dict[str, float]
    usage: Usage


def _summary_map(outputs: list[BaseAgentOutput]) -> dict[str, str]:
    return {o.agent_type.value: o.summary for o in outputs}


async def _argue(
    llm: LLMClient,
    speaker: AgentType,
    opponent: AgentType,
    speaker_view: str,
    opponent_view: str,
    stance: float,
) -> tuple[str, Usage]:
    side = "bullish" if stance >= 0.5 else "bearish"
    system = (
        f"You are the {speaker.value} analyst in an investment committee debate. "
        f"You hold a {side} view. Rebut the opposing analyst crisply in 1-2 sentences, "
        "using concrete reasoning. Do not concede without cause."
    )
    user = (
        f"Your position: {speaker_view}\n"
        f"Opposing ({opponent.value}) position: {opponent_view}\n"
        "Deliver your rebuttal."
    )
    arg, usage = await llm.structured(system=system, user=user, schema=ArgumentText)
    return arg.argument, usage


async def run_debate_round(
    round_no: int,
    stances: dict[str, float],
    outputs: list[BaseAgentOutput],
    llm: LLMClient,
    damping: float,
) -> RoundResult:
    summaries = _summary_map(outputs)
    bull = max(stances, key=stances.get)  # type: ignore[arg-type]
    bear = min(stances, key=stances.get)  # type: ignore[arg-type]
    bull_t, bear_t = AgentType(bull), AgentType(bear)

    total = Usage()
    turns: list[DebateTurn] = []

    bull_arg, u1 = await _argue(
        llm, bull_t, bear_t, summaries.get(bull, ""), summaries.get(bear, ""), stances[bull]
    )
    total = total + u1
    turns.append(
        DebateTurn(round=round_no, agent_type=bull_t, argument=bull_arg, rebuts=bear_t)
    )

    bear_arg, u2 = await _argue(
        llm, bear_t, bull_t, summaries.get(bear, ""), summaries.get(bull, ""), stances[bear]
    )
    total = total + u2
    turns.append(
        DebateTurn(round=round_no, agent_type=bear_t, argument=bear_arg, rebuts=bull_t)
    )

    # Converge both champions toward the group mean.
    center = mean(stances.values())
    new_stances = dict(stances)
    new_stances[bull] = round(stances[bull] + damping * (center - stances[bull]), 4)
    new_stances[bear] = round(stances[bear] + damping * (center - stances[bear]), 4)

    return RoundResult(round=round_no, turns=turns, stances=new_stances, usage=total)
