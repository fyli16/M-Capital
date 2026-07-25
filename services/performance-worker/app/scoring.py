"""Pure scoring functions — no I/O, fully unit-testable.

Correctness model:
  * A recommendation is "correct" if its realized 90-day EXCESS return (vs benchmark)
    matches its direction: buys want positive excess, sells want negative, holds want
    the position to have roughly tracked the benchmark (within ``hold_band``).
  * A contribution is "correct" if the agent's stance agreed with the outcome:
    ``was_correct = (agent_supported == recommendation_was_correct)``.
    This rewards good dissent — an agent that argued *against* a call that turned out
    wrong is scored correct (crucial for the adversarial Risk Officer).
"""

from __future__ import annotations

from aegis_shared.contracts import RecommendationAction

_BULLISH = {RecommendationAction.STRONG_BUY, RecommendationAction.BUY}
_BEARISH = {RecommendationAction.STRONG_SELL, RecommendationAction.SELL}


def horizon_return(p0: float | None, p1: float | None) -> float | None:
    if not p0 or p1 is None:
        return None
    return round(p1 / p0 - 1.0, 6)


def is_action_correct(
    action: RecommendationAction,
    ret_90d: float,
    benchmark_ret_90d: float,
    hold_band: float,
) -> bool:
    excess = ret_90d - benchmark_ret_90d
    if action in _BULLISH:
        return excess > 0
    if action in _BEARISH:
        return excess < 0
    return abs(excess) <= hold_band  # HOLD


def is_contribution_correct(supported: bool, action_correct: bool) -> bool:
    return supported == action_correct
