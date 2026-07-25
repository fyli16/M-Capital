"""Deterministic synthetic prices.

``price_on`` is a closed-form function of (ticker, day) — reproducible and
horizon-varying — so returns and correctness scoring are stable in tests and demos.
"""

from __future__ import annotations

import hashlib
import math
from datetime import datetime, timezone

_EPOCH = datetime(2000, 1, 1, tzinfo=timezone.utc)


def _seed(ticker: str) -> int:
    return int(hashlib.sha256(ticker.encode()).hexdigest()[:12], 16)


class SyntheticPrices:
    def price_on(self, ticker: str, when: datetime) -> float | None:
        s = _seed(ticker)
        if when.tzinfo is None:
            when = when.replace(tzinfo=timezone.utc)
        day = (when - _EPOCH).days

        base = 20.0 + (s % 880)                 # 20..900
        drift = 0.0002 + (s % 7) * 0.00005      # gentle per-day drift
        amp = 0.10 + (s % 5) * 0.03             # cyclical component
        phase = (s % 360) * math.pi / 180.0
        noise = ((s ^ day) % 100) / 100.0 * 0.02  # small deterministic wobble

        value = base * math.exp(drift * day) * (
            1 + amp * math.sin(day / 45.0 + phase) + noise
        )
        return round(value, 4)
