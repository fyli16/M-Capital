"""Orchestrates measurement: for each due recommendation, compute realized returns
across 30/60/90-day horizons and, once the 90-day window closes, score every agent
contribution."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import UUID

from .domain import DueRecommendation, PerfResult, ProcessSummary
from .prices import PriceProvider
from .scoring import horizon_return, is_action_correct, is_contribution_correct


class PerformanceRunner:
    def __init__(
        self,
        repo,
        prices: PriceProvider,
        *,
        benchmark_ticker: str,
        hold_band: float,
        min_age_days: int,
        batch_limit: int,
    ) -> None:
        self._repo = repo
        self._prices = prices
        self._benchmark = benchmark_ticker
        self._hold_band = hold_band
        self._min_age = min_age_days
        self._limit = batch_limit

    def process_due(self, now: datetime | None = None) -> ProcessSummary:
        now = now or datetime.now(timezone.utc)
        due = self._repo.due_recommendations(now, self._min_age, self._limit)
        summary = ProcessSummary()

        for rec in due:
            outcome = self._measure(rec, now)
            if outcome is None:
                summary.skipped += 1
                continue
            result, correctness = outcome
            self._repo.record_result(rec.id, result, correctness)
            summary.processed += 1
            if correctness:
                summary.finalized += 1

        return summary

    def _measure(
        self, rec: DueRecommendation, now: datetime
    ) -> tuple[PerfResult, dict[str, bool]] | None:
        p0 = self._prices.price_on(rec.ticker, rec.created_at)
        if p0 is None:
            return None  # cannot measure without an entry price

        r30 = self._horizon_return(rec.ticker, p0, rec.created_at, 30, now)
        r60 = self._horizon_return(rec.ticker, p0, rec.created_at, 60, now)
        r90 = self._horizon_return(rec.ticker, p0, rec.created_at, 90, now)

        benchmark_90: float | None = None
        correctness: dict[str, bool] = {}
        if r90 is not None:
            benchmark_90 = self._benchmark_return(rec.created_at, now)
            if benchmark_90 is not None:
                action_ok = is_action_correct(
                    rec.action, r90, benchmark_90, self._hold_band
                )
                correctness = {
                    c.agent_type: is_contribution_correct(c.supported, action_ok)
                    for c in rec.contributions
                }

        measured_at = now if (r90 is not None and benchmark_90 is not None) else None
        return (
            PerfResult(
                ret_30d=r30,
                ret_60d=r60,
                ret_90d=r90,
                benchmark_ret_90d=benchmark_90,
                measured_at=measured_at,
            ),
            correctness,
        )

    def _horizon_return(
        self, ticker: str, p0: float, start: datetime, days: int, now: datetime
    ) -> float | None:
        target = start + timedelta(days=days)
        if now < target:
            return None  # window hasn't elapsed yet
        return horizon_return(p0, self._prices.price_on(ticker, target))

    def _benchmark_return(self, start: datetime, now: datetime) -> float | None:
        b0 = self._prices.price_on(self._benchmark, start)
        b1 = self._prices.price_on(self._benchmark, start + timedelta(days=90))
        return horizon_return(b0, b1)
