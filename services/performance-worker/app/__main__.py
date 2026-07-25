"""CLI entry point for the performance-worker.

Designed to run as a scheduled task (EventBridge -> ECS Scheduled Task / cron):

    python -m app run          # measure due recommendations once
    python -m app backfill     # ignore the min-age gate (recompute unfinalized)
"""

from __future__ import annotations

import argparse
import logging
import sys

from .config import get_settings
from .prices import build_price_provider
from .repository import SqlPerformanceRepo
from .runner import PerformanceRunner

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("aegis.performance")


def _run(backfill: bool) -> int:
    settings = get_settings()
    if not settings.database_url:
        logger.error("DATABASE_URL is required")
        return 2

    repo = SqlPerformanceRepo(settings.database_url)
    runner = PerformanceRunner(
        repo=repo,
        prices=build_price_provider(settings),
        benchmark_ticker=settings.benchmark_ticker,
        hold_band=settings.hold_band,
        min_age_days=0 if backfill else settings.min_recommendation_age_days,
        batch_limit=settings.batch_limit,
    )
    summary = runner.process_due()
    logger.info(
        "performance run complete: processed=%d finalized=%d skipped=%d",
        summary.processed,
        summary.finalized,
        summary.skipped,
    )
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(prog="app", description="Aegis performance-worker")
    parser.add_argument(
        "command", nargs="?", default="run", choices=["run", "backfill"]
    )
    args = parser.parse_args()
    sys.exit(_run(backfill=args.command == "backfill"))


if __name__ == "__main__":
    main()
