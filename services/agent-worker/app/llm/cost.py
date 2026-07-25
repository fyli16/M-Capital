"""Token pricing and cost computation.

Prices are USD per 1,000 tokens (approximate list prices; update as vendors change).
Unknown models cost 0 so cost tracking degrades gracefully rather than erroring.
"""

from __future__ import annotations

# model -> (input_per_1k, output_per_1k)
_CHAT_PRICES: dict[str, tuple[float, float]] = {
    "gpt-4o": (0.0025, 0.010),
    "gpt-4o-mini": (0.00015, 0.0006),
    "gpt-4.1": (0.002, 0.008),
    "gpt-4.1-mini": (0.0004, 0.0016),
}

# model -> per_1k
_EMBED_PRICES: dict[str, float] = {
    "text-embedding-3-small": 0.00002,
    "text-embedding-3-large": 0.00013,
}


def chat_cost(model: str, tokens_in: int, tokens_out: int) -> float:
    price_in, price_out = _CHAT_PRICES.get(model, (0.0, 0.0))
    return (tokens_in / 1000.0) * price_in + (tokens_out / 1000.0) * price_out


def embed_cost(model: str, tokens: int) -> float:
    return (tokens / 1000.0) * _EMBED_PRICES.get(model, 0.0)
