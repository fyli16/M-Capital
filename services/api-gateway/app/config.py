"""API gateway configuration (env-driven, dev-friendly defaults)."""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "Aegis Capital API"
    environment: Literal["dev", "staging", "prod"] = "dev"

    # ---- Persistence / infra ----
    database_url: str | None = None
    redis_url: str | None = None

    # ---- Messaging (SQS) ----
    sqs_endpoint_url: str | None = None
    sqs_research_queue_url: str | None = None
    aws_region: str = "us-east-1"

    # ---- Auth ----
    jwt_secret: str = "change-me-in-prod"
    jwt_algorithm: str = "HS256"
    jwt_access_ttl_seconds: int = 900

    # ---- CORS ----
    cors_origins: list[str] = ["*"]

    # ---- Rate limiting ----
    rate_limit_backend: Literal["memory", "redis"] = "memory"
    rate_limit_requests: int = 60
    rate_limit_window_seconds: int = 60

    # ---- SSE ----
    sse_poll_interval_seconds: float = 1.0
    sse_max_seconds: int = 120


@lru_cache
def get_settings() -> Settings:
    return Settings()
