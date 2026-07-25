"""Public contracts surface."""

from .agents import (
    AnalystOutput,
    BaseAgentOutput,
    DebateTranscript,
    DebateTurn,
    Evidence,
    FinancialAnalystOutput,
    MacroAnalystOutput,
    NewsAnalystOutput,
    PortfolioManagerOutput,
    QuantAnalystOutput,
    RiskOfficerOutput,
)
from .api import (
    AgentRunView,
    AgentScorecard,
    CreateResearchRequest,
    HealthResponse,
    MemoryHit,
    MemorySearchRequest,
    MemorySearchResponse,
    PerformanceLeaderboard,
    RecommendationView,
    ResearchRequestAccepted,
    ResearchResultView,
)
from .enums import (
    ANALYST_AGENTS,
    AgentType,
    DebateOutcome,
    RecommendationAction,
    RequestStatus,
    RunStatus,
    UserRole,
)

__all__ = [
    # enums
    "ANALYST_AGENTS",
    "AgentType",
    "DebateOutcome",
    "RecommendationAction",
    "RequestStatus",
    "RunStatus",
    "UserRole",
    # agent contracts
    "AnalystOutput",
    "BaseAgentOutput",
    "DebateTranscript",
    "DebateTurn",
    "Evidence",
    "FinancialAnalystOutput",
    "MacroAnalystOutput",
    "NewsAnalystOutput",
    "PortfolioManagerOutput",
    "QuantAnalystOutput",
    "RiskOfficerOutput",
    # api dtos
    "AgentRunView",
    "AgentScorecard",
    "CreateResearchRequest",
    "HealthResponse",
    "MemoryHit",
    "MemorySearchRequest",
    "MemorySearchResponse",
    "PerformanceLeaderboard",
    "RecommendationView",
    "ResearchRequestAccepted",
    "ResearchResultView",
]
