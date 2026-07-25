"""Live point-in-time prices via Yahoo Finance (yfinance, lazy import)."""

from __future__ import annotations

from datetime import datetime, timedelta


class YahooPrices:
    """Closest available close within a few trading days of the target date."""

    def __init__(self, window_days: int = 5) -> None:
        self._window = window_days

    def price_on(self, ticker: str, when: datetime) -> float | None:
        import yfinance as yf

        start = (when - timedelta(days=self._window)).date()
        end = (when + timedelta(days=self._window)).date()
        try:
            hist = yf.Ticker(ticker).history(start=start, end=end, auto_adjust=True)
        except Exception:
            return None
        if hist is None or hist.empty or "Close" not in hist:
            return None
        closes = hist["Close"].dropna()
        if closes.empty:
            return None
        # Pick the trading day nearest to the target date.
        target = when.date()
        nearest = min(closes.index, key=lambda idx: abs((idx.date() - target).days))
        return round(float(closes.loc[nearest]), 4)
