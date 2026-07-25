"""Agent input/output contracts.

Every agent emits a *structured* payload validated against these models. LLM
free-text is coerced into these shapes via tool-calling / JSON mode; anything that
fails validation triggers one repair attempt and then an ABSTAIN.

Scores are normalized to ``[0, 1]`` (except ``sentiment_score`` which is signed
``[-1, 1]``). ``confidence`` is the agent's self-reported certainty and is used both
for synthesis weighting and for performance attribution.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from .enums import AgentType, RecommendationAction


class Evidence(BaseModel):
    """A single citation backing a claim."""

    model_config = ConfigDict(extra="forbid")

    claim: str = Field(..., description="The assertion this evidence supports.")
    source: str = Field(..., description="URL, filing id, or dataset reference.")
    excerpt: str | None = Field(default=None, description="Supporting quote/snippet.")


class BaseAgentOutput(BaseModel):
    """Fields common to every analyst output."""

    model_config = ConfigDict(extra="forbid")

    agent_type: AgentType
    confidence: float = Field(..., ge=0.0, le=1.0)
    sources: list[Evidence] = Field(default_factory=list)
    summary: str = Field(..., description="One-paragraph human-readable takeaway.")


class NewsAnalystOutput(BaseAgentOutput):
    agent_type: AgentType = AgentType.NEWS
    bullish_points: list[str] = Field(default_factory=list)
    bearish_points: list[str] = Field(default_factory=list)
    sentiment_score: float = Field(..., ge=-1.0, le=1.0, description="Signed sentiment.")


class FinancialAnalystOutput(BaseAgentOutput):
    agent_type: AgentType = AgentType.FINANCIAL
    fundamentals_score: float = Field(..., ge=0.0, le=1.0)
    valuation_score: float = Field(..., ge=0.0, le=1.0)
    strengths: list[str] = Field(default_factory=list)
    weaknesses: list[str] = Field(default_factory=list)


class QuantAnalystOutput(BaseAgentOutput):
    agent_type: AgentType = AgentType.QUANT
    quant_score: float = Field(..., ge=0.0, le=1.0)
    technical_signals: list[str] = Field(default_factory=list)
    risk_metrics: dict[str, float] = Field(
        default_factory=dict,
        description="e.g. {'sharpe': 1.4, 'volatility_30d': 0.28, 'beta': 1.7}.",
    )


class MacroAnalystOutput(BaseAgentOutput):
    agent_type: AgentType = AgentType.MACRO
    macro_score: float = Field(..., ge=0.0, le=1.0)
    opportunities: list[str] = Field(default_factory=list)
    threats: list[str] = Field(default_factory=list)


class RiskOfficerOutput(BaseAgentOutput):
    """Adversarial agent. High ``overall_risk_score`` means MORE danger."""

    agent_type: AgentType = AgentType.RISK
    overall_risk_score: float = Field(..., ge=0.0, le=1.0)
    dangers: list[str] = Field(default_factory=list)
    stress_scenarios: list[str] = Field(default_factory=list)


class PortfolioManagerOutput(BaseModel):
    """Final synthesized decision."""

    model_config = ConfigDict(extra="forbid")

    recommendation: RecommendationAction
    confidence: float = Field(..., ge=0.0, le=1.0)
    rationale: str
    key_risks: list[str] = Field(default_factory=list)
    supporting_factors: list[str] = Field(default_factory=list)


# ---- Debate contracts -------------------------------------------------------

class DebateTurn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    round: int = Field(..., ge=1)
    agent_type: AgentType
    argument: str
    rebuts: AgentType | None = Field(
        default=None, description="Which agent's position this turn challenges."
    )


class DebateTranscript(BaseModel):
    model_config = ConfigDict(extra="forbid")

    turns: list[DebateTurn] = Field(default_factory=list)
    rounds: int = Field(default=0, ge=0)


AnalystOutput = (
    NewsAnalystOutput
    | FinancialAnalystOutput
    | QuantAnalystOutput
    | MacroAnalystOutput
    | RiskOfficerOutput
)
