from app.config import Settings
from app.eval import EvalRunner
from app.eval.datasets import EvalCase
from app.graph import build_deps


async def _deps():
    return build_deps(Settings(llm_provider="fake"), enable_memory=False)


async def test_golden_set_passes():
    runner = EvalRunner(deps=await _deps())
    report = await runner.run()
    failures = [
        (c.ticker, m.name)
        for c in report.cases
        for m in c.metrics
        if not m.passed
    ]
    assert report.pass_rate == 1.0, f"eval failures: {failures}"


async def test_expected_action_snapshot_metric():
    # Provide a permissive expectation -> metric should pass.
    case = EvalCase(
        ticker="NVDA",
        expected_actions={"strong_buy", "buy", "hold", "sell", "strong_sell"},
    )
    report = await EvalRunner(deps=await _deps()).run([case])
    match = next(
        m for m in report.cases[0].metrics if m.name == "recommendation_matches_expected"
    )
    assert match.passed


async def test_judge_metric_when_enabled():
    runner = EvalRunner(deps=await _deps(), judge_enabled=True)
    report = await runner.run([EvalCase(ticker="AAPL")])
    names = {m.name for m in report.cases[0].metrics}
    assert "judge_rationale_grounding" in names
    assert report.cases[0].passed


async def test_determinism_metric_present():
    report = await EvalRunner(deps=await _deps()).run([EvalCase(ticker="MSFT")])
    det = next(m for m in report.cases[0].metrics if m.name == "deterministic")
    assert det.passed
