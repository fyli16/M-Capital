"""Deterministic synthetic providers (default; offline; used for tests and fallback).

Data is seeded by ticker so results are stable across runs — invaluable for
reproducible tests and demos without network access.
"""

from __future__ import annotations

import hashlib
import random
import statistics

from .base import (
    Fundamentals,
    FilingsData,
    MarketData,
    NewsData,
)


def _rng(ticker: str, salt: str = "") -> random.Random:
    seed = int(hashlib.sha256(f"{ticker}:{salt}".encode()).hexdigest()[:16], 16)
    return random.Random(seed)


class SyntheticMarketData:
    def fetch(self, ticker: str) -> MarketData:
        rng = _rng(ticker, "market")
        daily = [rng.gauss(0.0006, 0.02) for _ in range(252)]
        ann_vol = statistics.pstdev(daily) * (252 ** 0.5)
        ann_ret = sum(daily)
        sharpe = (statistics.mean(daily) / (statistics.pstdev(daily) or 1e-9)) * (252 ** 0.5)
        equity, peak, mdd = 1.0, 1.0, 0.0
        for r in daily:
            equity *= 1 + r
            peak = max(peak, equity)
            mdd = min(mdd, equity / peak - 1)
        return MarketData(
            last_price=round(rng.uniform(20, 900), 2),
            momentum_3m=round(sum(daily[-63:]), 4),
            momentum_12m=round(ann_ret, 4),
            volatility_annual=round(ann_vol, 4),
            sharpe=round(sharpe, 3),
            beta=round(rng.uniform(0.7, 1.9), 2),
            max_drawdown=round(mdd, 4),
            source="synthetic",
        )


class SyntheticFundamentals:
    def fetch(self, ticker: str) -> Fundamentals:
        rng = _rng(ticker, "fund")
        return Fundamentals(
            revenue_growth_yoy=round(rng.uniform(-0.1, 0.6), 3),
            gross_margin=round(rng.uniform(0.3, 0.75), 3),
            net_margin=round(rng.uniform(-0.05, 0.35), 3),
            fcf_margin=round(rng.uniform(-0.02, 0.3), 3),
            debt_to_equity=round(rng.uniform(0.0, 2.2), 2),
            pe_ratio=round(rng.uniform(8, 65), 1),
            source="synthetic",
        )


class SyntheticNews:
    def fetch(self, ticker: str) -> NewsData:
        rng = _rng(ticker, "news")
        templates = [
            ("{t} beats quarterly estimates", "Reuters"),
            ("Analysts raise price target on {t}", "Bloomberg"),
            ("{t} faces regulatory review in key market", "WSJ"),
            ("Supply constraints ease for {t}", "FT"),
            ("Insider selling reported at {t}", "Barron's"),
        ]
        headlines = []
        for title, source in rng.sample(templates, 4):
            headlines.append(
                {
                    "title": title.format(t=ticker),
                    "sentiment": round(rng.uniform(-0.8, 0.9), 2),
                    "source": source,
                }
            )
        agg = round(statistics.mean(h["sentiment"] for h in headlines), 3)
        return NewsData(aggregate_sentiment=agg, headlines=headlines, source="synthetic")


class SyntheticFilings:
    def fetch(self, ticker: str) -> FilingsData:
        rng = _rng(ticker, "sec")
        pool = [
            "Dependence on a limited number of customers",
            "Exposure to foreign currency fluctuations",
            "Intense competition and rapid technological change",
            "Reliance on third-party manufacturing capacity",
            "Potential impact of new export regulations",
            "Concentration of supply in a single region",
        ]
        return FilingsData(
            risk_factors=rng.sample(pool, 3), latest_form="10-Q", source="synthetic"
        )
