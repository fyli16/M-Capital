"""Shared enumerations.

These are the canonical vocabulary of the platform. They are declared as
``str``-based enums so the *same values* serialize cleanly to JSON (API/contracts)
and persist as ``TEXT`` in Postgres guarded by ``CHECK`` constraints.

Design note: we intentionally use ``TEXT + CHECK`` rather than native Postgres
``ENUM`` types. Altering a Postgres enum (e.g. adding a recommendation tier) requires
``ALTER TYPE ... ADD VALUE`` which cannot run inside a transaction and is awkward to
roll back. ``TEXT + CHECK`` gives us the same integrity with painless migrations.
"""

from __future__ import annotations

from enum import Enum


class UserRole(str, Enum):
    VIEWER = "viewer"
    ANALYST = "analyst"
    ADMIN = "admin"


class RequestStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    DEBATING = "debating"
    COMPLETE = "complete"
    FAILED = "failed"


class AgentType(str, Enum):
    NEWS = "news"
    FINANCIAL = "financial"
    QUANT = "quant"
    MACRO = "macro"
    RISK = "risk"
    PORTFOLIO_MANAGER = "portfolio_manager"


class RunStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETE = "complete"
    FAILED = "failed"
    ABSTAINED = "abstained"  # agent timed out / produced invalid output; excluded from synthesis


class RecommendationAction(str, Enum):
    STRONG_BUY = "strong_buy"
    BUY = "buy"
    HOLD = "hold"
    SELL = "sell"
    STRONG_SELL = "strong_sell"


class DebateOutcome(str, Enum):
    NO_CONFLICT = "no_conflict"      # phase 1 already agreed; debate skipped
    CONSENSUS = "consensus"          # agents converged during debate
    CONVERGED = "converged"          # score variance dropped below threshold
    MAX_ROUNDS = "max_rounds"        # stopped by round cap, unresolved


# The set of analyst agents that feed the Portfolio Manager (excludes the PM itself).
ANALYST_AGENTS: tuple[AgentType, ...] = (
    AgentType.NEWS,
    AgentType.FINANCIAL,
    AgentType.QUANT,
    AgentType.MACRO,
    AgentType.RISK,
)
