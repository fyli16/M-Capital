"""Worker configuration (env-driven, with dev-friendly defaults).

Everything has a default so the graph runs locally with the ``fake`` LLM and no
external services. Production overrides come from environment variables / secrets.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # ---- LLM ----
    llm_provider: Literal["fake", "openai"] = "fake"
    openai_api_key: str | None = None
    openai_model: str = "gpt-4o"
    openai_embedding_model: str = "text-embedding-3-small"
    embedding_dim: int = 1536
    llm_temperature: float = 0.2

    # ---- Data providers ----
    data_provider: Literal["synthetic", "live"] = "synthetic"
    sec_user_agent: str = ""  # required for live EDGAR: 'Name Company email@example.com'

    # ---- Observability (OpenTelemetry) ----
    otel_enabled: bool = False
    otel_exporter_otlp_endpoint: str | None = None
    otel_service_name: str = "aegis-agent-worker"
    metrics_export_interval_ms: int = 15000

    # ---- LangSmith ----
    langsmith_tracing: bool = False
    langsmith_api_key: str | None = None
    langsmith_project: str = "aegis-capital"

    # ---- Persistence / infra ----
    database_url: str | None = None
    redis_url: str | None = None

    # ---- Messaging (SQS) ----
    sqs_endpoint_url: str | None = None
    sqs_research_queue_url: str | None = None
    aws_region: str = "us-east-1"
    sqs_wait_seconds: int = 20
    sqs_visibility_timeout: int = 300

    # ---- Debate tuning ----
    conflict_threshold: float = 0.35     # stance spread that triggers debate
    converge_threshold: float = 0.15     # stance spread that ends debate
    debate_damping: float = 0.30         # how far champions move toward the mean per round
    default_max_rounds: int = 3

    # ---- Resilience ----
    agent_timeout_seconds: float = 60.0
    tool_cache_ttl_seconds: int = 900


@lru_cache
def get_settings() -> Settings:
    return Settings()
