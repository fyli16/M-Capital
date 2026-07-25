"""Performance-worker configuration."""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str | None = None

    # ---- Prices ----
    price_provider: Literal["synthetic", "live"] = "synthetic"
    benchmark_ticker: str = "SPY"

    # ---- Measurement policy ----
    min_recommendation_age_days: int = 30  # don't process until at least this old
    hold_band: float = 0.05                # ±5% excess return counts as "HOLD correct"
    batch_limit: int = 500


@lru_cache
def get_settings() -> Settings:
    return Settings()
