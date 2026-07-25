"""SQLAlchemy ORM models — the persistence backbone of Aegis Capital.

Enum-like columns are stored as ``TEXT`` guarded by ``CHECK`` constraints (see
``contracts.enums`` for rationale). Vectors use pgvector with an HNSW index defined
in the Alembic migration.

Relationship map::

    users 1─* research_requests 1─* agent_runs 1─1 agent_outputs
                     │
                     ├─1 debates 1─* debate_turns
                     ├─1 recommendations 1─* performance_tracking
                     │                   1─* agent_contributions
                     └─* memories 1─1 embeddings
"""

from __future__ import annotations

import uuid
from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..contracts.enums import (
    AgentType,
    DebateOutcome,
    RecommendationAction,
    RequestStatus,
    RunStatus,
    UserRole,
)
from .base import Base, PKMixin, TimestampMixin

EMBEDDING_DIM = 1536  # OpenAI text-embedding-3-small


def _check(values: type, column: str) -> CheckConstraint:
    """Build a CHECK constraint restricting ``column`` to a str-enum's values."""
    allowed = ", ".join(f"'{m.value}'" for m in values)  # type: ignore[attr-defined]
    return CheckConstraint(f"{column} IN ({allowed})", name=f"ck_{column}")


class User(PKMixin, TimestampMixin, Base):
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(320), unique=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(
        String(32), nullable=False, default=UserRole.ANALYST.value
    )

    requests: Mapped[list["ResearchRequest"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )

    __table_args__ = (_check(UserRole, "role"),)


class ResearchRequest(PKMixin, TimestampMixin, Base):
    __tablename__ = "research_requests"

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    ticker: Mapped[str] = mapped_column(String(12), nullable=False, index=True)
    status: Mapped[str] = mapped_column(
        String(16), nullable=False, default=RequestStatus.QUEUED.value, index=True
    )
    params: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)

    user: Mapped["User"] = relationship(back_populates="requests")
    agent_runs: Mapped[list["AgentRun"]] = relationship(
        back_populates="request", cascade="all, delete-orphan"
    )
    debate: Mapped["Debate | None"] = relationship(
        back_populates="request", cascade="all, delete-orphan", uselist=False
    )
    recommendation: Mapped["Recommendation | None"] = relationship(
        back_populates="request", cascade="all, delete-orphan", uselist=False
    )
    memories: Mapped[list["Memory"]] = relationship(
        back_populates="request", cascade="all, delete-orphan"
    )

    __table_args__ = (_check(RequestStatus, "status"),)


class AgentRun(PKMixin, TimestampMixin, Base):
    """One execution of one agent within a request (telemetry + status)."""

    __tablename__ = "agent_runs"

    request_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("research_requests.id", ondelete="CASCADE"), nullable=False
    )
    agent_type: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(
        String(16), nullable=False, default=RunStatus.PENDING.value
    )
    tokens_in: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    tokens_out: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    cost_usd: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)

    request: Mapped["ResearchRequest"] = relationship(back_populates="agent_runs")
    output: Mapped["AgentOutput | None"] = relationship(
        back_populates="run", cascade="all, delete-orphan", uselist=False
    )

    __table_args__ = (
        _check(AgentType, "agent_type"),
        _check(RunStatus, "status"),
        UniqueConstraint("request_id", "agent_type", name="uq_agent_run_per_request"),
    )


class AgentOutput(PKMixin, TimestampMixin, Base):
    """The validated structured payload produced by an agent run."""

    __tablename__ = "agent_outputs"

    run_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("agent_runs.id", ondelete="CASCADE"), nullable=False, unique=True
    )
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    sources: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)

    run: Mapped["AgentRun"] = relationship(back_populates="output")

    __table_args__ = (
        CheckConstraint("confidence >= 0 AND confidence <= 1", name="ck_output_conf"),
    )


class Debate(PKMixin, TimestampMixin, Base):
    __tablename__ = "debates"

    request_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("research_requests.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    rounds: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    outcome: Mapped[str] = mapped_column(
        String(16), nullable=False, default=DebateOutcome.NO_CONFLICT.value
    )

    request: Mapped["ResearchRequest"] = relationship(back_populates="debate")
    turns: Mapped[list["DebateTurn"]] = relationship(
        back_populates="debate",
        cascade="all, delete-orphan",
        order_by="DebateTurn.round",
    )

    __table_args__ = (_check(DebateOutcome, "outcome"),)


class DebateTurn(PKMixin, TimestampMixin, Base):
    __tablename__ = "debate_turns"

    debate_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("debates.id", ondelete="CASCADE"), nullable=False
    )
    round: Mapped[int] = mapped_column(Integer, nullable=False)
    agent_type: Mapped[str] = mapped_column(String(32), nullable=False)
    argument: Mapped[str] = mapped_column(Text, nullable=False)
    rebuts: Mapped[str | None] = mapped_column(String(32), nullable=True)

    debate: Mapped["Debate"] = relationship(back_populates="turns")

    __table_args__ = (
        _check(AgentType, "agent_type"),
        Index("ix_debate_turns_debate_round", "debate_id", "round"),
    )


class Recommendation(PKMixin, TimestampMixin, Base):
    __tablename__ = "recommendations"

    request_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("research_requests.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    ticker: Mapped[str] = mapped_column(String(12), nullable=False, index=True)
    action: Mapped[str] = mapped_column(String(16), nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    rationale: Mapped[str] = mapped_column(Text, nullable=False)
    key_risks: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    supporting_factors: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)

    request: Mapped["ResearchRequest"] = relationship(back_populates="recommendation")
    performance: Mapped[list["PerformanceTracking"]] = relationship(
        back_populates="recommendation", cascade="all, delete-orphan"
    )
    contributions: Mapped[list["AgentContribution"]] = relationship(
        back_populates="recommendation", cascade="all, delete-orphan"
    )

    __table_args__ = (
        _check(RecommendationAction, "action"),
        CheckConstraint("confidence >= 0 AND confidence <= 1", name="ck_rec_conf"),
    )


class PerformanceTracking(PKMixin, TimestampMixin, Base):
    """Realized returns measured after a recommendation, vs a benchmark."""

    __tablename__ = "performance_tracking"

    recommendation_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("recommendations.id", ondelete="CASCADE"), nullable=False
    )
    ret_30d: Mapped[float | None] = mapped_column(Float, nullable=True)
    ret_60d: Mapped[float | None] = mapped_column(Float, nullable=True)
    ret_90d: Mapped[float | None] = mapped_column(Float, nullable=True)
    benchmark_ret_90d: Mapped[float | None] = mapped_column(Float, nullable=True)
    measured_at: Mapped[datetime | None] = mapped_column(nullable=True)

    recommendation: Mapped["Recommendation"] = relationship(back_populates="performance")


class AgentContribution(PKMixin, TimestampMixin, Base):
    """Attributes a recommendation outcome back to each contributing agent.

    Powers the leaderboards: per-agent accuracy, avg confidence, calibration.
    """

    __tablename__ = "agent_contributions"

    recommendation_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("recommendations.id", ondelete="CASCADE"), nullable=False
    )
    agent_type: Mapped[str] = mapped_column(String(32), nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    supported: Mapped[bool] = mapped_column(
        Boolean, nullable=False, comment="Did this agent support the final action?"
    )
    was_correct: Mapped[bool | None] = mapped_column(
        Boolean, nullable=True, comment="Set once outcome is known (nullable until then)."
    )

    recommendation: Mapped["Recommendation"] = relationship(back_populates="contributions")

    __table_args__ = (
        _check(AgentType, "agent_type"),
        UniqueConstraint(
            "recommendation_id", "agent_type", name="uq_contribution_per_agent"
        ),
    )


class Memory(PKMixin, TimestampMixin, Base):
    """Long-term episodic memory: a summarized analysis, retrievable semantically."""

    __tablename__ = "memories"

    request_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("research_requests.id", ondelete="SET NULL"), nullable=True
    )
    ticker: Mapped[str] = mapped_column(String(12), nullable=False, index=True)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    content: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)

    request: Mapped["ResearchRequest | None"] = relationship(back_populates="memories")
    embedding: Mapped["Embedding | None"] = relationship(
        back_populates="memory", cascade="all, delete-orphan", uselist=False
    )


class Embedding(PKMixin, TimestampMixin, Base):
    """Vector representation of a memory. HNSW-indexed (see migration)."""

    __tablename__ = "embeddings"

    memory_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("memories.id", ondelete="CASCADE"), nullable=False, unique=True
    )
    model: Mapped[str] = mapped_column(String(64), nullable=False)
    embedding: Mapped[list[float]] = mapped_column(Vector(EMBEDDING_DIM), nullable=False)

    memory: Mapped["Memory"] = relationship(back_populates="embedding")
