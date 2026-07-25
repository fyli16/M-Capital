"""Deterministic offline LLM.

``FakeLLM`` fabricates schema-valid outputs seeded by the prompt, so:
  * the full LangGraph pipeline runs with no API keys or network,
  * tests are deterministic (same prompt -> same output),
  * local development has realistic-looking data.

It dispatches on ``schema.__name__`` (no imports of the agent layer, avoiding
circular dependencies) and falls back to a generic fabricator for unknown schemas.
"""

from __future__ import annotations

import hashlib
import math
import random
from typing import Any, TypeVar

from pydantic import BaseModel

from .base import Usage

T = TypeVar("T", bound=BaseModel)

_BULL = [
    "Accelerating revenue growth outpaces sector peers",
    "Expanding gross margins signal pricing power",
    "Strong free cash flow funds buybacks",
    "Dominant market share in a secular-growth category",
    "Upbeat management guidance for next quarter",
]
_BEAR = [
    "Valuation multiples stretched versus history",
    "Customer concentration raises revenue risk",
    "Rising input costs pressure margins",
    "Regulatory scrutiny could cap expansion",
    "Decelerating unit growth in core segment",
]
_SIGNALS = [
    "Golden cross on the 50/200-day moving averages",
    "RSI in neutral territory (52)",
    "Positive 3-month price momentum",
    "Volume expansion on up-days",
]
_MACRO_OPP = ["Easing rate cycle supports multiples", "Sector tailwind from AI capex"]
_MACRO_THREAT = ["Sticky core inflation", "Elevated long-end yields", "FX headwinds"]
_DANGERS = [
    "Earnings miss would compress the multiple sharply",
    "Geopolitical export controls threaten key markets",
    "Single-supplier dependency in the supply chain",
]
_STRESS = [
    "-30% drawdown if guidance is cut",
    "Multiple de-rates to sector median (-18%)",
    "Demand air-pocket halves growth for two quarters",
]


def _rng(system: str, user: str) -> random.Random:
    digest = hashlib.sha256(f"{system}\x00{user}".encode()).hexdigest()
    return random.Random(int(digest[:16], 16))


def _sample(rng: random.Random, pool: list[str], k: int) -> list[str]:
    k = max(1, min(k, len(pool)))
    return rng.sample(pool, k)


class FakeLLM:
    """A deterministic, offline ``LLMClient`` implementation."""

    def __init__(self, model: str = "fake-1", embedding_dim: int = 1536) -> None:
        self.model = model
        self._dim = embedding_dim

    async def structured(
        self, *, system: str, user: str, schema: type[T]
    ) -> tuple[T, Usage]:
        rng = _rng(system, user)
        data = self._fabricate(schema.__name__, rng)
        if data is None:
            data = self._generic(schema, rng)
        obj = schema.model_validate(data)
        usage = Usage(
            tokens_in=len(system) // 4 + len(user) // 4,
            tokens_out=32,
            cost_usd=0.0,
        )
        return obj, usage

    async def embed(self, text: str) -> tuple[list[float], Usage]:
        rng = _rng("embed", text)
        vec = [rng.uniform(-1.0, 1.0) for _ in range(self._dim)]
        norm = math.sqrt(sum(v * v for v in vec)) or 1.0
        return [v / norm for v in vec], Usage(tokens_in=len(text) // 4)

    # -- known-schema builders -------------------------------------------------

    def _fabricate(self, name: str, rng: random.Random) -> dict[str, Any] | None:
        conf = round(rng.uniform(0.55, 0.9), 3)
        builders = {
            "NewsAnalystOutput": lambda: {
                "confidence": conf,
                "summary": "Sentiment skews constructive on strong product cycle.",
                "bullish_points": _sample(rng, _BULL, rng.randint(2, 3)),
                "bearish_points": _sample(rng, _BEAR, rng.randint(1, 2)),
                "sentiment_score": round(rng.uniform(-0.4, 0.7), 3),
            },
            "FinancialAnalystOutput": lambda: {
                "confidence": conf,
                "summary": "Fundamentals are solid with premium valuation.",
                "fundamentals_score": round(rng.uniform(0.4, 0.9), 3),
                "valuation_score": round(rng.uniform(0.2, 0.7), 3),
                "strengths": _sample(rng, _BULL, 2),
                "weaknesses": _sample(rng, _BEAR, 2),
            },
            "QuantAnalystOutput": lambda: {
                "confidence": conf,
                "summary": "Momentum positive; volatility elevated.",
                "quant_score": round(rng.uniform(0.35, 0.85), 3),
                "technical_signals": _sample(rng, _SIGNALS, rng.randint(2, 3)),
                "risk_metrics": {
                    "sharpe": round(rng.uniform(0.5, 2.2), 2),
                    "volatility_annual": round(rng.uniform(0.2, 0.55), 2),
                    "beta": round(rng.uniform(0.8, 1.9), 2),
                },
            },
            "MacroAnalystOutput": lambda: {
                "confidence": conf,
                "summary": "Macro backdrop mixed but sector-supportive.",
                "macro_score": round(rng.uniform(0.35, 0.75), 3),
                "opportunities": _sample(rng, _MACRO_OPP, rng.randint(1, 2)),
                "threats": _sample(rng, _MACRO_THREAT, rng.randint(1, 2)),
            },
            "RiskOfficerOutput": lambda: {
                "confidence": conf,
                "summary": "Material downside risks warrant caution.",
                "overall_risk_score": round(rng.uniform(0.35, 0.8), 3),
                "dangers": _sample(rng, _DANGERS, rng.randint(2, 3)),
                "stress_scenarios": _sample(rng, _STRESS, rng.randint(1, 2)),
            },
            "PMNarrative": lambda: {
                "rationale": (
                    "Weighing analyst conviction against the Risk Officer's objections, "
                    "the balance of evidence supports the stated action."
                ),
                "key_risks": _sample(rng, _DANGERS, 2),
                "supporting_factors": _sample(rng, _BULL, 2),
            },
            "ArgumentText": lambda: {
                "argument": _sample(rng, _BULL + _BEAR, 1)[0]
                + " — this materially shifts the risk/reward."
            },
            "JudgeScore": lambda: {
                "score": 4,
                "reason": "Rationale is consistent with the analyst findings.",
            },
        }
        builder = builders.get(name)
        return builder() if builder else None

    # -- generic fallback ------------------------------------------------------

    def _generic(self, schema: type[BaseModel], rng: random.Random) -> dict[str, Any]:
        out: dict[str, Any] = {}
        for fname, field in schema.model_fields.items():
            ann = field.annotation
            if ann in (float,):
                out[fname] = round(rng.uniform(0.0, 1.0), 3)
            elif ann in (int,):
                out[fname] = rng.randint(0, 5)
            elif ann in (bool,):
                out[fname] = bool(rng.getrandbits(1))
            elif ann in (str,):
                out[fname] = "generated"
            elif ann in (list, list[str]):
                out[fname] = ["generated"]
        return out
