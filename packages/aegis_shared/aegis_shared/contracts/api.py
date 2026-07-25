"""API-layer DTOs (request/response envelopes for the FastAPI gateway).

These are deliberately separate from the persistence models: the wire contract
should evolve independently from the database schema.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from .agents import (
    DebateTranscript,
    FinancialAnalystOutput,
    MacroAnalystOutput,
    NewsAnalystOutput,
    PortfolioManagerOutput,
    QuantAnalystOutput,
    RiskOfficerOutput,
)
from .enums import AgentType, RecommendationAction, RequestStatus, RunStatus

TICKER_PATTERN = r"^[A-Z][A-Z0-9.\-]{0,9}$"


# ---- Research submission ----------------------------------------------------

class CreateResearchRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ticker: str = Field(..., pattern=TICKER_PATTERN, examples=["NVDA"])
    enable_debate: bool = Field(default=True)
    max_debate_rounds: int = Field(default=3, ge=0, le=5)


class ResearchRequestAccepted(BaseModel):
    """202 response: work is enqueued, results arrive asynchronously."""

    request_id: UUID
    status: RequestStatus
    stream_url: str = Field(..., description="SSE endpoint for live progress.")


# ---- Agent run views --------------------------------------------------------

class AgentRunView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    agent_type: AgentType
    status: RunStatus
    confidence: float | None = None
    latency_ms: int | None = None
    tokens_in: int | None = None
    tokens_out: int | None = None
    output: dict | None = Field(default=None, description="Validated agent payload.")


# ---- Full research result ---------------------------------------------------

class RecommendationView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    ticker: str
    action: RecommendationAction
    confidence: float
    rationale: str
    key_risks: list[str] = Field(default_factory=list)
    supporting_factors: list[str] = Field(default_factory=list)
    created_at: datetime


class ResearchResultView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    request_id: UUID
    ticker: str
    status: RequestStatus
    created_at: datetime
    agent_runs: list[AgentRunView] = Field(default_factory=list)
    debate: DebateTranscript | None = None
    recommendation: RecommendationView | None = None


# ---- Performance / leaderboards ---------------------------------------------

class AgentScorecard(BaseModel):
    agent_type: AgentType
    total_contributions: int
    accuracy: float = Field(..., ge=0.0, le=1.0, description="Fraction correct.")
    avg_confidence: float = Field(..., ge=0.0, le=1.0)
    calibration_gap: float = Field(
        ..., description="avg_confidence - accuracy; >0 means overconfident."
    )


class PerformanceLeaderboard(BaseModel):
    scorecards: list[AgentScorecard]
    best_agent: AgentType | None = None
    worst_agent: AgentType | None = None


# ---- Memory search ----------------------------------------------------------

class MemorySearchRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    query: str = Field(..., min_length=3)
    ticker: str | None = Field(default=None, pattern=TICKER_PATTERN)
    limit: int = Field(default=10, ge=1, le=50)


class MemoryHit(BaseModel):
    memory_id: UUID
    ticker: str
    summary: str
    created_at: datetime
    similarity: float = Field(..., ge=0.0, le=1.0)


class MemorySearchResponse(BaseModel):
    query: str
    hits: list[MemoryHit]


# ---- Health / metrics -------------------------------------------------------

class HealthResponse(BaseModel):
    status: str = "ok"
    database: bool
    redis: bool
    queue: bool


# Re-export agent outputs so consumers get one import surface for the wire types.
__all__ = [
    "CreateResearchRequest",
    "ResearchRequestAccepted",
    "AgentRunView",
    "RecommendationView",
    "ResearchResultView",
    "AgentScorecard",
    "PerformanceLeaderboard",
    "MemorySearchRequest",
    "MemoryHit",
    "MemorySearchResponse",
    "HealthResponse",
    "NewsAnalystOutput",
    "FinancialAnalystOutput",
    "QuantAnalystOutput",
    "MacroAnalystOutput",
    "RiskOfficerOutput",
    "PortfolioManagerOutput",
]
