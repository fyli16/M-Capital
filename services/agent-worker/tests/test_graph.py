from aegis_shared.contracts import AgentType, RecommendationAction

from app.runner import run_analysis


async def test_full_pipeline_produces_recommendation(deps):
    state = await run_analysis(
        "NVDA", deps=deps, enable_debate=True, max_debate_rounds=3
    )

    rec = state["recommendation"]
    assert rec is not None
    assert rec.recommendation in set(RecommendationAction)
    assert 0.0 <= rec.confidence <= 1.0
    assert rec.rationale


async def test_all_agents_execute(deps):
    state = await run_analysis("MSFT", deps=deps)

    agent_types = [r.agent_type for r in state["agent_runs"]]
    analysts = [a for a in agent_types if a != AgentType.PORTFOLIO_MANAGER]

    assert AgentType.PORTFOLIO_MANAGER in agent_types
    assert len(analysts) == 5
    assert set(analysts) == {
        AgentType.NEWS,
        AgentType.FINANCIAL,
        AgentType.QUANT,
        AgentType.MACRO,
        AgentType.RISK,
    }


async def test_deterministic_for_same_ticker(deps):
    a = await run_analysis("AAPL", deps=deps)
    b = await run_analysis("AAPL", deps=deps)
    assert a["recommendation"].recommendation == b["recommendation"].recommendation
    assert a["stances"] == b["stances"]


async def test_debate_can_be_disabled(deps):
    state = await run_analysis("TSLA", deps=deps, enable_debate=False)
    assert state.get("debate_turns", []) == []
    assert state["recommendation"] is not None
