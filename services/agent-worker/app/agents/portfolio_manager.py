"""Portfolio Manager: the final decision maker.

Design choice worth calling out: the **decision is computed deterministically** from
the analysts' (post-debate) stances weighted by confidence; the **LLM only writes the
narrative** (rationale, key risks, supporting factors). This grounds the recommendation
in transparent, auditable math — the model narrates, it does not invent the number.
"""

from __future__ import annotations

from statistics import mean

from pydantic import BaseModel, ConfigDict, Field

from aegis_shared.contracts import (
    AgentType,
    BaseAgentOutput,
    DebateTurn,
    PortfolioManagerOutput,
    RecommendationAction,
)

from ..debate.conflict import stance_of
from ..llm import LLMClient, Usage


class PMNarrative(BaseModel):
    """The text the LLM authors around a pre-computed decision."""

    model_config = ConfigDict(extra="forbid")

    rationale: str
    key_risks: list[str] = Field(default_factory=list)
    supporting_factors: list[str] = Field(default_factory=list)


def action_from_score(score: float) -> RecommendationAction:
    if score >= 0.75:
        return RecommendationAction.STRONG_BUY
    if score >= 0.60:
        return RecommendationAction.BUY
    if score >= 0.40:
        return RecommendationAction.HOLD
    if score >= 0.25:
        return RecommendationAction.SELL
    return RecommendationAction.STRONG_SELL


def aggregate(
    outputs: list[BaseAgentOutput], stances: dict[str, float]
) -> tuple[RecommendationAction, float, float]:
    """Return (action, confidence, bullishness_score)."""
    if not outputs:
        return RecommendationAction.HOLD, 0.1, 0.5

    used: list[float] = []
    num = den = 0.0
    for o in outputs:
        s = stances.get(o.agent_type.value, stance_of(o))
        used.append(s)
        num += s * o.confidence
        den += o.confidence

    score = num / den if den else mean(used)
    spread = (max(used) - min(used)) if used else 0.0
    avg_conf = mean(o.confidence for o in outputs)
    confidence = max(0.05, min(0.99, avg_conf * (1.0 - 0.5 * spread)))
    return action_from_score(score), round(confidence, 3), round(score, 3)


class PortfolioManager:
    agent_type = AgentType.PORTFOLIO_MANAGER

    def system_prompt(self) -> str:
        return (
            "You are the Portfolio Manager. A quantitative aggregation of the analyst "
            "team (already accounting for the debate) has produced a recommendation. "
            "Write a concise, defensible rationale, list the key risks that could "
            "invalidate the thesis, and the strongest supporting factors. Do not change "
            "the decision; explain it honestly, including dissent."
        )

    def user_prompt(
        self,
        ticker: str,
        outputs: list[BaseAgentOutput],
        debate_turns: list[DebateTurn],
        action: RecommendationAction,
        score: float,
    ) -> str:
        summaries = "\n".join(
            f"- {o.agent_type.value}: {o.summary} (confidence {o.confidence:.2f})"
            for o in outputs
        )
        debate = (
            "\n".join(
                f"  R{t.round} {t.agent_type.value}"
                + (f" vs {t.rebuts.value}" if t.rebuts else "")
                + f": {t.argument}"
                for t in debate_turns
            )
            or "  (no debate — analysts were aligned)"
        )
        return (
            f"Ticker: {ticker}\n"
            f"Computed decision: {action.value} (bullishness score {score:.2f})\n\n"
            f"Analyst findings:\n{summaries}\n\n"
            f"Debate transcript:\n{debate}\n"
        )

    async def narrate(
        self,
        ticker: str,
        outputs: list[BaseAgentOutput],
        debate_turns: list[DebateTurn],
        action: RecommendationAction,
        confidence: float,
        score: float,
        llm: LLMClient,
    ) -> tuple[PortfolioManagerOutput, Usage]:
        """Author the narrative around an already-decided action/confidence.

        The decision is computed by the synthesis node from *post-debate* stances and
        passed in here; the LLM never changes the number, only explains it.
        """
        narrative, usage = await llm.structured(
            system=self.system_prompt(),
            user=self.user_prompt(ticker, outputs, debate_turns, action, score),
            schema=PMNarrative,
        )
        decision = PortfolioManagerOutput(
            recommendation=action,
            confidence=confidence,
            rationale=narrative.rationale,
            key_risks=narrative.key_risks,
            supporting_factors=narrative.supporting_factors,
        )
        return decision, usage
