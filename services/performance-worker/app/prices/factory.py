"""Selects the configured price provider (synthetic default; live -> Yahoo)."""

from __future__ import annotations

import logging

from ..config import Settings
from .base import PriceProvider
from .synthetic import SyntheticPrices

logger = logging.getLogger("aegis.performance.prices")


def build_price_provider(settings: Settings) -> PriceProvider:
    if settings.price_provider == "live":
        try:
            from .yahoo import YahooPrices

            return YahooPrices()
        except Exception as exc:  # pragma: no cover
            logger.warning("live prices unavailable (%s); using synthetic", exc)
    return SyntheticPrices()
