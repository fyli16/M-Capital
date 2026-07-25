from aegis_shared.contracts import (
    NewsAnalystOutput,
    QuantAnalystOutput,
    RiskOfficerOutput,
)

from app.debate import detect_conflict, run_debate_round, stance_of
from app.llm import FakeLLM


def _bullish_news() -> NewsAnalystOutput:
    return NewsAnalystOutput(
        confidence=0.8, summary="Very positive", sentiment_score=0.9
    )


def _bearish_risk() -> RiskOfficerOutput:
    return RiskOfficerOutput(
        confidence=0.8, summary="Dangerous", overall_risk_score=0.9
    )


def _neutral_quant() -> QuantAnalystOutput:
    return QuantAnalystOutput(confidence=0.7, summary="Mixed", quant_score=0.5)


def test_stance_mapping_inverts_risk():
    assert stance_of(_bullish_news()) > 0.8   # bullish
    assert stance_of(_bearish_risk()) < 0.2   # adversarial -> bearish


def test_conflict_detected_on_wide_spread():
    report = detect_conflict(
        [_bullish_news(), _bearish_risk(), _neutral_quant()], threshold=0.35
    )
    assert report.has_conflict
    assert report.bull_champion is not None
    assert report.bear_champion is not None


def test_no_conflict_when_aligned():
    report = detect_conflict(
        [_bullish_news(), _neutral_quant()], threshold=0.9
    )
    assert not report.has_conflict


async def test_debate_round_reduces_spread():
    outputs = [_bullish_news(), _bearish_risk(), _neutral_quant()]
    report = detect_conflict(outputs, threshold=0.35)

    result = await run_debate_round(
        1, report.stances, outputs, FakeLLM(), damping=0.3
    )

    new_spread = max(result.stances.values()) - min(result.stances.values())
    assert new_spread < report.spread          # converging
    assert len(result.turns) == 2              # bull + bear rebuttals
    assert result.turns[0].argument
