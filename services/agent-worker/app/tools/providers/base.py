"""Data-provider ports (protocols) and the value objects they return.

The analyst agents depend only on these dataclasses; swapping synthetic data for
live sources (Yahoo Finance, SEC EDGAR) is purely an adapter change. Every value
object carries a ``source`` so downstream code and observability can tell whether a
figure came from a real feed or a synthetic fallback.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable


@dataclass
class MarketData:
    last_price: float
    momentum_3m: float
    momentum_12m: float
    volatility_annual: float
    sharpe: float
    beta: float
    max_drawdown: float
    source: str = "synthetic"


@dataclass
class Fundamentals:
    revenue_growth_yoy: float
    gross_margin: float
    net_margin: float
    fcf_margin: float
    debt_to_equity: float
    pe_ratio: float
    source: str = "synthetic"


@dataclass
class NewsData:
    aggregate_sentiment: float
    headlines: list[dict] = field(default_factory=list)  # {title, sentiment, source}
    source: str = "synthetic"


@dataclass
class FilingsData:
    risk_factors: list[str] = field(default_factory=list)
    latest_form: str = "10-Q"
    source: str = "synthetic"


@runtime_checkable
class MarketDataProvider(Protocol):
    def fetch(self, ticker: str) -> MarketData: ...


@runtime_checkable
class FundamentalsProvider(Protocol):
    def fetch(self, ticker: str) -> Fundamentals: ...


@runtime_checkable
class NewsProvider(Protocol):
    def fetch(self, ticker: str) -> NewsData: ...


@runtime_checkable
class FilingsProvider(Protocol):
    def fetch(self, ticker: str) -> FilingsData: ...


@dataclass
class DataProviders:
    """Bundle of the four data sources injected into ``gather_tool_context``."""

    market: MarketDataProvider
    fundamentals: FundamentalsProvider
    news: NewsProvider
    filings: FilingsProvider
