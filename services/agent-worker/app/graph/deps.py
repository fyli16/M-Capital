"""Dependency container injected into graph nodes (closures capture this)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable

from ..agents import AnalystAgent, PortfolioManager, build_analysts
from ..config import Settings, get_settings
from ..llm import LLMClient, build_llm
from ..memory import MemoryStore
from ..observability import NoopTelemetry, Telemetry, build_telemetry
from ..tools.cache import Cache, InMemoryTTLCache
from ..tools.providers import DataProviders, build_providers


@dataclass
class Deps:
    settings: Settings
    llm: LLMClient
    analysts: list[AnalystAgent]
    pm: PortfolioManager
    providers: DataProviders
    telemetry: Telemetry = field(default_factory=NoopTelemetry)
    cache: Cache | None = None
    memory: MemoryStore | None = None
    # optional persistence hook: async callable(state) -> None
    persistence: Callable[[Any], Awaitable[None]] | None = None


def build_deps(
    settings: Settings | None = None,
    *,
    enable_memory: bool = True,
) -> Deps:
    settings = settings or get_settings()
    llm = build_llm(settings)

    memory: MemoryStore | None = None
    if enable_memory and settings.database_url:
        memory = MemoryStore(
            database_url=settings.database_url,
            embedder=llm,
            model=(
                settings.openai_embedding_model
                if settings.llm_provider == "openai"
                else "fake-embed"
            ),
        )

    return Deps(
        settings=settings,
        llm=llm,
        analysts=build_analysts(),
        pm=PortfolioManager(),
        providers=build_providers(settings),
        telemetry=build_telemetry(settings),
        cache=InMemoryTTLCache(),
        memory=memory,
    )
