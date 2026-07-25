"""OpenAI adapter implementing the ``LLMClient`` protocol.

Uses the SDK's structured-output parsing so responses are guaranteed to match the
requested Pydantic schema. The ``openai`` import is lazy so the worker doesn't
require the SDK unless this provider is actually selected.
"""

from __future__ import annotations

from typing import TypeVar

from pydantic import BaseModel
from tenacity import retry, stop_after_attempt, wait_exponential

from .base import LLMError, Usage
from .cost import chat_cost, embed_cost

T = TypeVar("T", bound=BaseModel)


class OpenAIClient:
    def __init__(
        self,
        api_key: str,
        model: str,
        embedding_model: str,
        temperature: float = 0.2,
    ) -> None:
        try:
            from openai import AsyncOpenAI
        except ImportError as exc:  # pragma: no cover - import guard
            raise LLMError(
                "openai package not installed; `pip install .[openai]`"
            ) from exc
        self._client = AsyncOpenAI(api_key=api_key)
        self.model = model
        self._embedding_model = embedding_model
        self._temperature = temperature

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        reraise=True,
    )
    async def structured(
        self, *, system: str, user: str, schema: type[T]
    ) -> tuple[T, Usage]:
        resp = await self._client.beta.chat.completions.parse(
            model=self.model,
            temperature=self._temperature,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            response_format=schema,
        )
        message = resp.choices[0].message
        if getattr(message, "refusal", None):
            raise LLMError(f"Model refused: {message.refusal}")
        parsed = message.parsed
        if parsed is None:
            raise LLMError("Model returned no parseable content")
        u = resp.usage
        usage = Usage(
            tokens_in=u.prompt_tokens if u else 0,
            tokens_out=u.completion_tokens if u else 0,
            cost_usd=chat_cost(
                self.model,
                u.prompt_tokens if u else 0,
                u.completion_tokens if u else 0,
            ),
        )
        return parsed, usage

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        reraise=True,
    )
    async def embed(self, text: str) -> tuple[list[float], Usage]:
        resp = await self._client.embeddings.create(
            model=self._embedding_model, input=text
        )
        tokens = resp.usage.total_tokens if resp.usage else 0
        usage = Usage(
            tokens_in=tokens,
            cost_usd=embed_cost(self._embedding_model, tokens),
        )
        return resp.data[0].embedding, usage
