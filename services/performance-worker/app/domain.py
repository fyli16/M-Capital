"""Lightweight domain objects that decouple the runner from the ORM."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID

from aegis_shared.contracts import RecommendationAction


@dataclass
class ContributionRef:
    agent_type: str
    supported: bool


@dataclass
class DueRecommendation:
    id: UUID
    ticker: str
    action: RecommendationAction
    created_at: datetime
    contributions: list[ContributionRef] = field(default_factory=list)


@dataclass
class PerfResult:
    ret_30d: float | None
    ret_60d: float | None
    ret_90d: float | None
    benchmark_ret_90d: float | None
    measured_at: datetime | None


@dataclass
class ProcessSummary:
    processed: int = 0
    finalized: int = 0   # 90d window complete -> contributions scored
    skipped: int = 0     # price data unavailable
