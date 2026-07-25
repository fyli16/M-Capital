from datetime import datetime, timedelta, timezone
from uuid import uuid4

from aegis_shared.contracts import RecommendationAction

from app.domain import ContributionRef, DueRecommendation, PerfResult
from app.runner import PerformanceRunner


class FakeRepo:
    def __init__(self, due):
        self._due = due
        self.recorded: dict = {}

    def due_recommendations(self, now, min_age_days, limit):
        return self._due

    def record_result(self, rec_id, result: PerfResult, correctness: dict):
        self.recorded[rec_id] = (result, correctness)


class LinearPrices:
    """Deterministic fake: <ticker>@created = base, then +slope per day.

    Benchmark ("SPY") stays flat so excess return == the ticker's return.
    """

    def __init__(self, created: datetime):
        self._created = created

    def price_on(self, ticker, when):
        if ticker == "SPY":
            return 100.0
        days = (when - self._created).days
        return 100.0 * (1 + 0.003 * days)  # ~+27% at 90 days


def _rec(created, action, contribs):
    return DueRecommendation(
        id=uuid4(), ticker="NVDA", action=action, created_at=created, contributions=contribs
    )


def _runner(repo, prices):
    return PerformanceRunner(
        repo=repo,
        prices=prices,
        benchmark_ticker="SPY",
        hold_band=0.05,
        min_age_days=30,
        batch_limit=100,
    )


def test_finalizes_and_scores_after_90_days():
    now = datetime(2026, 7, 1, tzinfo=timezone.utc)
    created = now - timedelta(days=100)
    contribs = [
        ContributionRef("news", supported=True),   # backed the BUY
        ContributionRef("risk", supported=False),   # dissented
    ]
    rec = _rec(created, RecommendationAction.BUY, contribs)
    repo = FakeRepo([rec])

    summary = _runner(repo, LinearPrices(created)).process_due(now)

    assert summary.processed == 1
    assert summary.finalized == 1
    result, correctness = repo.recorded[rec.id]
    assert result.ret_90d is not None and result.ret_90d > 0
    assert result.benchmark_ret_90d == 0.0
    assert result.measured_at == now
    # BUY was correct (beat flat benchmark): supporter correct, dissenter incorrect
    assert correctness["news"] is True
    assert correctness["risk"] is False


def test_partial_window_not_finalized():
    now = datetime(2026, 7, 1, tzinfo=timezone.utc)
    created = now - timedelta(days=40)  # 30d elapsed, 60/90 not yet
    rec = _rec(created, RecommendationAction.BUY, [ContributionRef("news", True)])
    repo = FakeRepo([rec])

    summary = _runner(repo, LinearPrices(created)).process_due(now)

    assert summary.processed == 1
    assert summary.finalized == 0
    result, correctness = repo.recorded[rec.id]
    assert result.ret_30d is not None
    assert result.ret_60d is None
    assert result.ret_90d is None
    assert correctness == {}


def test_skips_when_no_entry_price():
    now = datetime(2026, 7, 1, tzinfo=timezone.utc)
    created = now - timedelta(days=100)
    rec = _rec(created, RecommendationAction.BUY, [ContributionRef("news", True)])
    repo = FakeRepo([rec])

    class NoPrices:
        def price_on(self, ticker, when):
            return None

    summary = _runner(repo, NoPrices()).process_due(now)
    assert summary.skipped == 1
    assert summary.processed == 0
    assert repo.recorded == {}
