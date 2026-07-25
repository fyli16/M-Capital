"""Selects and constructs the configured LLM provider."""

from __future__ import annotations

from ..config import Settings
from .base import LLMClient, LLMError
from .fake_client import FakeLLM


def build_llm(settings: Settings) -> LLMClient:
    if settings.llm_provider == "fake":
        return FakeLLM(model="fake-1", embedding_dim=settings.embedding_dim)

    if settings.llm_provider == "openai":
        if not settings.openai_api_key:
            raise LLMError("OPENAI_API_KEY is required when llm_provider='openai'")
        from .openai_client import OpenAIClient

        return OpenAIClient(
            api_key=settings.openai_api_key,
            model=settings.openai_model,
            embedding_model=settings.openai_embedding_model,
            temperature=settings.llm_temperature,
        )

    raise LLMError(f"Unknown llm_provider: {settings.llm_provider}")
