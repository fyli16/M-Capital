"""Runs the agent pipeline over a dataset and aggregates metric results.

Also checks *determinism* by running each case twice and comparing the decision —
a cheap but powerful regression signal with the deterministic fake LLM.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from ..graph import Deps, build_deps
from ..runner import run_analysis
from .datasets import GOLDEN, EvalCase
from .judge import judge_rationale
from .metrics import ALL_METRICS, MetricResult


@dataclass
class CaseReport:
    ticker: str
    metrics: list[MetricResult] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return all(m.passed for m in self.metrics)


@dataclass
class EvalReport:
    cases: list[CaseReport] = field(default_factory=list)

    @property
    def total(self) -> int:
        return len(self.cases)

    @property
    def passed(self) -> int:
        return sum(1 for c in self.cases if c.passed)

    @property
    def pass_rate(self) -> float:
        return self.passed / self.total if self.total else 0.0


class EvalRunner:
    def __init__(self, deps: Deps | None = None, judge_enabled: bool = False) -> None:
        self._deps = deps or build_deps(enable_memory=False)
        self._judge = judge_enabled

    async def run(self, cases: list[EvalCase] | None = None) -> EvalReport:
        cases = cases or GOLDEN
        report = EvalReport()
        for case in cases:
            report.cases.append(await self._run_case(case))
        return report

    async def _run_case(self, case: EvalCase) -> CaseReport:
        state = await run_analysis(
            case.ticker,
            deps=self._deps,
            enable_debate=case.enable_debate,
            max_debate_rounds=case.max_rounds,
        )
        cr = CaseReport(ticker=case.ticker)
        cr.metrics = [metric(case, state) for metric in ALL_METRICS]

        # Determinism: a second run must reach the same decision & stances.
        again = await run_analysis(
            case.ticker,
            deps=self._deps,
            enable_debate=case.enable_debate,
            max_debate_rounds=case.max_rounds,
        )
        same = (
            state.get("recommendation") is not None
            and again.get("recommendation") is not None
            and state["recommendation"].recommendation
            == again["recommendation"].recommendation
            and state.get("stances") == again.get("stances")
        )
        cr.metrics.append(
            MetricResult("deterministic", same, 1.0 if same else 0.0)
        )

        if self._judge:
            judgement, _ = await judge_rationale(state, self._deps.llm)
            cr.metrics.append(
                MetricResult(
                    "judge_rationale_grounding",
                    judgement.score >= 3,
                    judgement.score / 5.0,
                    f"score={judgement.score}: {judgement.reason}",
                )
            )
        return cr
