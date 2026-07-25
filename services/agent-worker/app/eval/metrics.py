"""Evaluators. Each takes an ``EvalCase`` and the final ``GraphState`` and returns a
``MetricResult``. These are the regression gate for the agent pipeline."""

from __future__ import annotations

from dataclasses import dataclass

from aegis_shared.contracts import AgentType, RecommendationAction

from ..graph.state import GraphState
from .datasets import EvalCase

VALID_ACTIONS = {a.value for a in RecommendationAction}


@dataclass
class MetricResult:
    name: str
    passed: bool
    score: float
    detail: str = ""


def _analysts(state: GraphState):
    return [r for r in state.get("agent_runs", []) if r.agent_type != AgentType.PORTFOLIO_MANAGER]


def all_agents_ran(case: EvalCase, state: GraphState) -> MetricResult:
    analysts = _analysts(state)
    has_pm = any(
        r.agent_type == AgentType.PORTFOLIO_MANAGER for r in state.get("agent_runs", [])
    )
    ok = len(analysts) == 5 and has_pm
    return MetricResult(
        "all_agents_ran", ok, 1.0 if ok else 0.0,
        f"{len(analysts)} analysts, pm={has_pm}",
    )


def outputs_valid(case: EvalCase, state: GraphState) -> MetricResult:
    outs = state.get("analyst_outputs", [])
    bad = [o for o in outs if not (0.0 <= o.confidence <= 1.0)]
    ok = len(outs) >= 1 and not bad
    return MetricResult(
        "outputs_valid", ok, 1.0 if ok else 0.0,
        f"{len(outs)} outputs, {len(bad)} out-of-range",
    )


def risk_officer_adversarial(case: EvalCase, state: GraphState) -> MetricResult:
    risk = next(
        (o for o in state.get("analyst_outputs", []) if o.agent_type == AgentType.RISK),
        None,
    )
    ok = risk is not None and hasattr(risk, "overall_risk_score") and 0.0 <= risk.overall_risk_score <= 1.0
    return MetricResult(
        "risk_officer_adversarial", ok, 1.0 if ok else 0.0,
        "risk output present with valid risk score" if ok else "missing/invalid risk output",
    )


def recommendation_valid(case: EvalCase, state: GraphState) -> MetricResult:
    rec = state.get("recommendation")
    ok = (
        rec is not None
        and rec.recommendation.value in VALID_ACTIONS
        and 0.0 <= rec.confidence <= 1.0
        and bool(rec.rationale)
    )
    return MetricResult(
        "recommendation_valid", ok, 1.0 if ok else 0.0,
        rec.recommendation.value if rec else "none",
    )


def recommendation_matches_expected(case: EvalCase, state: GraphState) -> MetricResult:
    if not case.expected_actions:
        return MetricResult("recommendation_matches_expected", True, 1.0, "n/a")
    rec = state.get("recommendation")
    action = rec.recommendation.value if rec else None
    ok = action in case.expected_actions
    return MetricResult(
        "recommendation_matches_expected", ok, 1.0 if ok else 0.0,
        f"{action} in {sorted(case.expected_actions)}",
    )


def debate_bounded(case: EvalCase, state: GraphState) -> MetricResult:
    rounds = state.get("debate_round", 0)
    turns = state.get("debate_turns", [])
    outcome = state.get("debate_outcome")
    within_cap = rounds <= case.max_rounds
    outcome_ok = (not turns) or outcome in {"converged", "consensus", "max_rounds"}
    ok = within_cap and outcome_ok
    return MetricResult(
        "debate_bounded", ok, 1.0 if ok else 0.0,
        f"rounds={rounds}/{case.max_rounds} outcome={outcome}",
    )


def calibration_sane(case: EvalCase, state: GraphState) -> MetricResult:
    rec = state.get("recommendation")
    ok = rec is not None and 0.05 <= rec.confidence <= 0.99
    return MetricResult(
        "calibration_sane", ok, 1.0 if ok else 0.0,
        f"pm_confidence={rec.confidence if rec else 'none'}",
    )


ALL_METRICS = [
    all_agents_ran,
    outputs_valid,
    risk_officer_adversarial,
    recommendation_valid,
    recommendation_matches_expected,
    debate_bounded,
    calibration_sane,
]
