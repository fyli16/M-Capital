"""Live market/fundamentals/news providers backed by Yahoo Finance (yfinance).

Heavy imports (yfinance/pandas/vaderSentiment) are lazy so the worker only pulls
them when the ``live`` provider is actually selected. Any data gap raises, which the
factory's fallback wrapper turns into synthetic data (never a broken run).
"""

from __future__ import annotations

import math

from .base import Fundamentals, MarketData, NewsData

_TRADING_DAYS = 252


def _yf_ticker(ticker: str):
    import yfinance as yf

    return yf.Ticker(ticker)


class YahooMarketData:
    def fetch(self, ticker: str) -> MarketData:
        t = _yf_ticker(ticker)
        hist = t.history(period="1y", auto_adjust=True)
        if hist is None or hist.empty or "Close" not in hist:
            raise RuntimeError(f"No price history for {ticker}")

        close = hist["Close"].dropna()
        returns = close.pct_change().dropna()
        if len(returns) < 20:
            raise RuntimeError(f"Insufficient history for {ticker}")

        mean_r = float(returns.mean())
        std_r = float(returns.std()) or 1e-9
        cum = (1 + returns).cumprod()
        drawdown = float((cum / cum.cummax() - 1).min())

        mom_3m = (
            float(close.iloc[-1] / close.iloc[-63] - 1) if len(close) > 63 else float(cum.iloc[-1] - 1)
        )
        info = _safe_info(t)
        beta = _as_float(info.get("beta"), default=1.0)

        return MarketData(
            last_price=round(float(close.iloc[-1]), 2),
            momentum_3m=round(mom_3m, 4),
            momentum_12m=round(float(cum.iloc[-1] - 1), 4),
            volatility_annual=round(std_r * math.sqrt(_TRADING_DAYS), 4),
            sharpe=round((mean_r / std_r) * math.sqrt(_TRADING_DAYS), 3),
            beta=round(beta, 2),
            max_drawdown=round(drawdown, 4),
            source="yahoo",
        )


class YahooFundamentals:
    def fetch(self, ticker: str) -> Fundamentals:
        t = _yf_ticker(ticker)
        info = _safe_info(t)
        if not info:
            raise RuntimeError(f"No fundamentals for {ticker}")

        revenue = _as_float(info.get("totalRevenue"))
        fcf = _as_float(info.get("freeCashflow"))
        fcf_margin = (fcf / revenue) if (revenue and fcf) else _as_float(
            info.get("operatingMargins"), default=0.0
        )
        d2e = _as_float(info.get("debtToEquity"))

        return Fundamentals(
            revenue_growth_yoy=round(_as_float(info.get("revenueGrowth"), 0.0), 3),
            gross_margin=round(_as_float(info.get("grossMargins"), 0.0), 3),
            net_margin=round(_as_float(info.get("profitMargins"), 0.0), 3),
            fcf_margin=round(fcf_margin, 3),
            debt_to_equity=round(d2e / 100.0 if d2e else 0.0, 2),
            pe_ratio=round(_as_float(info.get("trailingPE"), 0.0), 1),
            source="yahoo",
        )


class YahooNews:
    """Yahoo headlines scored with VADER (offline, no API key)."""

    def __init__(self, max_headlines: int = 8) -> None:
        self._max = max_headlines

    def fetch(self, ticker: str) -> NewsData:
        from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

        t = _yf_ticker(ticker)
        raw = getattr(t, "news", None) or []
        analyzer = SentimentIntensityAnalyzer()

        headlines: list[dict] = []
        for item in raw[: self._max]:
            content = item.get("content", item)  # yfinance schema varies by version
            title = content.get("title") or item.get("title")
            if not title:
                continue
            publisher = (
                content.get("provider", {}).get("displayName")
                if isinstance(content.get("provider"), dict)
                else item.get("publisher")
            ) or "Yahoo"
            sentiment = analyzer.polarity_scores(title)["compound"]
            headlines.append(
                {"title": title, "sentiment": round(sentiment, 3), "source": publisher}
            )

        if not headlines:
            raise RuntimeError(f"No news for {ticker}")

        agg = round(sum(h["sentiment"] for h in headlines) / len(headlines), 3)
        return NewsData(aggregate_sentiment=agg, headlines=headlines, source="yahoo")


def _safe_info(t) -> dict:
    try:
        return dict(t.info or {})
    except Exception:
        return {}


def _as_float(value, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default
