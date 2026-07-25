"""Price provider port: closing price for a ticker on (or near) a given date."""

from __future__ import annotations

from datetime import datetime
from typing import Protocol, runtime_checkable


@runtime_checkable
class PriceProvider(Protocol):
    def price_on(self, ticker: str, when: datetime) -> float | None: ...
