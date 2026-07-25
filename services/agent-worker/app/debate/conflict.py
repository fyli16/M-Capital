"""Maps each analyst output to a normalized *bullishness* stance in [0, 1] and
detects whether the team disagrees enough to warrant a debate.

Stance convention: 0 = maximally bearish, 1 = maximally bullish.
The Risk Officer is inverted (high risk -> low bullishness).
"""

from __future__ import annotations

from statistics import pstdev

from pydantic import BaseModel

from aegis_shared.contracts import (
    AgentType,
    BaseAgentOutput,
    FinancialAnalystOutput,
    MacroAnalystOutput,
    NewsAnalystOutput,
    QuantAnalystOutput,
    RiskOfficerOutput,
)


def stance_of(output: BaseAgentOutput) -> float:
    """Project an analyst's output onto a [0, 1] bullishness axis."""
    if isinstance(output, NewsAnalystOutput):
        return (output.sentiment_score + 1.0) / 2.0
    if isinstance(output, FinancialAnalystOutput):
        return (output.fundamentals_score + output.valuation_score) / 2.0
    if isinstance(output, QuantAnalystOutput):
        return output.quant_score
    if isinstance(output, MacroAnalystOutput):
        return output.macro_score
    if isinstance(output, RiskOfficerOutput):
        return 1.0 - output.overall_risk_score  # adversarial: high risk = bearish
    return 0.5


class ConflictReport(BaseModel):
    has_conflict: bool
    spread: float
    stddev: float
    stances: dict[str, float]
    bull_champion: AgentType | None = None
    bear_champion: AgentType | None = None


def detect_conflict(
    outputs: list[BaseAgentOutput], threshold: float
) -> ConflictReport:
    stances = {o.agent_type.value: round(stance_of(o), 4) for o in outputs}
    if len(stances) < 2:
        return ConflictReport(
            has_conflict=False, spread=0.0, stddev=0.0, stances=stances
        )

    values = list(stances.values())
    spread = max(values) - min(values)
    std = pstdev(values)
    bull = max(stances, key=stances.get)  # type: ignore[arg-type]
    bear = min(stances, key=stances.get)  # type: ignore[arg-type]

    return ConflictReport(
        has_conflict=spread >= threshold,
        spread=round(spread, 4),
        stddev=round(std, 4),
        stances=stances,
        bull_champion=AgentType(bull),
        bear_champion=AgentType(bear),
    )
