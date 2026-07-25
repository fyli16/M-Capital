"""Golden evaluation dataset.

Cases are intentionally invariant-based rather than exact-match: with the fake LLM
the pipeline is deterministic, but the evaluators assert *structural and behavioral*
properties that must hold for any correct run (and remain meaningful with a real LLM).
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class EvalCase:
    ticker: str
    enable_debate: bool = True
    max_rounds: int = 3
    # Optional golden snapshot: if set, the final action must be in this set.
    expected_actions: set[str] | None = None


GOLDEN: list[EvalCase] = [
    EvalCase(ticker="NVDA"),
    EvalCase(ticker="AAPL"),
    EvalCase(ticker="MSFT"),
    EvalCase(ticker="TSLA"),
    EvalCase(ticker="AMD", max_rounds=3),
    EvalCase(ticker="KO", enable_debate=False),
]
