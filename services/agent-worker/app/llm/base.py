"""LLM client protocol and shared value objects."""

from __future__ import annotations

from typing import Protocol, TypeVar, runtime_checkable

from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)


class Usage(BaseModel):
    """Token accounting for one or more LLM calls."""

    tokens_in: int = 0
    tokens_out: int = 0
    cost_usd: float = 0.0

    def __add__(self, other: "Usage") -> "Usage":
        return Usage(
            tokens_in=self.tokens_in + other.tokens_in,
            tokens_out=self.tokens_out + other.tokens_out,
            cost_usd=self.cost_usd + other.cost_usd,
        )


class LLMError(RuntimeError):
    """Raised when the provider refuses, errors, or returns unparseable output."""


@runtime_checkable
class LLMClient(Protocol):
    """Structured-output LLM interface.

    ``structured`` MUST return an instance of ``schema`` or raise ``LLMError``.
    Callers rely on this to guarantee agent outputs conform to their contracts.
    """

    model: str

    async def structured(
        self, *, system: str, user: str, schema: type[T]
    ) -> tuple[T, Usage]: ...

    async def embed(self, text: str) -> tuple[list[float], Usage]: ...
