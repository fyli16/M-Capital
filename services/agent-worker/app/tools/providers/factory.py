"""Builds the ``DataProviders`` bundle from settings, wrapping live providers with
synthetic fallback so a flaky feed degrades gracefully instead of failing the run."""

from __future__ import annotations

import logging
from typing import Any

from ...config import Settings
from .base import DataProviders
from .synthetic import (
    SyntheticFilings,
    SyntheticFundamentals,
    SyntheticMarketData,
    SyntheticNews,
)

logger = logging.getLogger("aegis.worker.providers")


class _Fallback:
    """Try the primary provider; on any error, log and use the fallback."""

    def __init__(self, name: str, primary: Any, fallback: Any) -> None:
        self._name = name
        self._primary = primary
        self._fallback = fallback

    def fetch(self, ticker: str):
        try:
            return self._primary.fetch(ticker)
        except Exception as exc:
            logger.warning(
                "live %s provider failed for %s (%s); using synthetic",
                self._name,
                ticker,
                exc,
            )
            return self._fallback.fetch(ticker)


def _synthetic_bundle() -> DataProviders:
    return DataProviders(
        market=SyntheticMarketData(),
        fundamentals=SyntheticFundamentals(),
        news=SyntheticNews(),
        filings=SyntheticFilings(),
    )


def build_providers(settings: Settings) -> DataProviders:
    if settings.data_provider != "live":
        return _synthetic_bundle()

    from .edgar import EdgarFilings
    from .yahoo import YahooFundamentals, YahooMarketData, YahooNews

    syn = _synthetic_bundle()

    # EDGAR construction can fail (missing user-agent); fall back for filings only.
    try:
        edgar: Any = EdgarFilings(settings.sec_user_agent)
    except Exception as exc:
        logger.warning("EDGAR disabled (%s); using synthetic filings", exc)
        edgar = syn.filings

    return DataProviders(
        market=_Fallback("market", YahooMarketData(), syn.market),
        fundamentals=_Fallback("fundamentals", YahooFundamentals(), syn.fundamentals),
        news=_Fallback("news", YahooNews(), syn.news),
        filings=_Fallback("filings", edgar, syn.filings),
    )
