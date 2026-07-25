"""Eval CLI — a CI-gateable regression check for the agent pipeline.

    python -m app.eval                 # run golden set, exit 1 if anything fails
    python -m app.eval --judge         # also run LLM-as-judge
    python -m app.eval --json
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys

from .runner import EvalReport, EvalRunner


def _print(report: EvalReport) -> None:
    for case in report.cases:
        mark = "PASS" if case.passed else "FAIL"
        print(f"\n[{mark}] {case.ticker}")
        for m in case.metrics:
            status = "ok " if m.passed else "XX "
            print(f"   {status} {m.name:<32} {m.detail}")
    print(
        f"\n{report.passed}/{report.total} cases passed "
        f"({report.pass_rate:.0%})"
    )


async def _main(judge: bool, as_json: bool) -> int:
    report = await EvalRunner(judge_enabled=judge).run()
    if as_json:
        print(
            json.dumps(
                {
                    "pass_rate": report.pass_rate,
                    "passed": report.passed,
                    "total": report.total,
                    "cases": [
                        {
                            "ticker": c.ticker,
                            "passed": c.passed,
                            "metrics": [
                                {"name": m.name, "passed": m.passed, "detail": m.detail}
                                for m in c.metrics
                            ],
                        }
                        for c in report.cases
                    ],
                },
                indent=2,
            )
        )
    else:
        _print(report)
    return 0 if report.passed == report.total else 1


def main() -> None:
    parser = argparse.ArgumentParser(prog="app.eval")
    parser.add_argument("--judge", action="store_true", help="run LLM-as-judge metric")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    sys.exit(asyncio.run(_main(args.judge, args.json)))


if __name__ == "__main__":
    main()
