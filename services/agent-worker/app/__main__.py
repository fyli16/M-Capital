"""CLI: run a single analysis locally.

    python -m app --ticker NVDA
    python -m app --ticker AAPL --rounds 2 --json
    python -m app consume            # start the SQS worker loop
"""

from __future__ import annotations

import argparse
import asyncio
import json

from .config import get_settings
from .graph import build_deps
from .runner import run_analysis


def _print_report(state) -> None:
    rec = state.get("recommendation")
    print(f"\n=== M Capital - {state['ticker']} ===")
    if rec is not None:
        print(f"Recommendation : {rec.recommendation.value.upper()}")
        print(f"Confidence     : {rec.confidence:.0%}")
        print(f"Rationale      : {rec.rationale}")
        if rec.key_risks:
            print("Key risks      : " + "; ".join(rec.key_risks))

    print("\nAgents:")
    for r in state.get("agent_runs", []):
        conf = f"{r.confidence:.0%}" if r.confidence is not None else "  -"
        print(
            f"  {r.agent_type.value:<18} {r.status.value:<10} conf={conf:>4} "
            f"tok={r.tokens_in + r.tokens_out:<5} {r.latency_ms or 0}ms"
        )

    turns = state.get("debate_turns", [])
    if turns:
        print(f"\nDebate ({state.get('debate_outcome')}, {state.get('debate_round')} rounds):")
        for t in turns:
            vs = f" vs {t.rebuts.value}" if t.rebuts else ""
            print(f"  R{t.round} {t.agent_type.value}{vs}: {t.argument}")


async def _run(args) -> None:
    settings = get_settings()
    deps = build_deps(settings, enable_memory=bool(settings.database_url))
    state = await run_analysis(
        ticker=args.ticker,
        deps=deps,
        enable_debate=not args.no_debate,
        max_debate_rounds=args.rounds,
    )
    if args.json:
        rec = state.get("recommendation")
        print(
            json.dumps(
                {
                    "ticker": state["ticker"],
                    "recommendation": rec.recommendation.value if rec else None,
                    "confidence": rec.confidence if rec else None,
                    "debate_outcome": state.get("debate_outcome"),
                    "agents": [
                        {
                            "agent": r.agent_type.value,
                            "status": r.status.value,
                            "confidence": r.confidence,
                        }
                        for r in state.get("agent_runs", [])
                    ],
                },
                indent=2,
            )
        )
    else:
        _print_report(state)


def main() -> None:
    parser = argparse.ArgumentParser(prog="app", description="Aegis agent-worker")
    sub = parser.add_subparsers(dest="command")
    sub.add_parser("consume", help="Run the SQS consumer loop")

    parser.add_argument("--ticker", default="NVDA")
    parser.add_argument("--rounds", type=int, default=None)
    parser.add_argument("--no-debate", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    if args.command == "consume":
        from .consumer import SqsConsumer

        asyncio.run(SqsConsumer().poll_forever())
        return

    asyncio.run(_run(args))


if __name__ == "__main__":
    main()
