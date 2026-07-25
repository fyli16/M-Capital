# ADR 0002 — LangGraph for agent orchestration

**Status:** Accepted

## Context

Five analyst agents must run in parallel, fan into a barrier, conditionally enter a
bounded debate loop, and then hand off to a Portfolio Manager. This is a stateful
graph with parallelism, conditional branches, and loops — not a linear chain. It must
also survive worker crashes mid-run.

## Decision

Model the workflow as a **LangGraph `StateGraph`**. Parallel analyst branches use an
`operator.add` reducer to append into shared list channels without clobbering each
other; a barrier node fans them in; conditional edges implement the debate loop with a
convergence gate and round cap. Orchestration (the graph) is separated from execution
(a worker pool consuming from SQS), and graph state is serializable so runs can resume.

## Consequences

- **Positive:** native support for parallel fan-out/fan-in, conditional loops, and checkpointing.
- **Positive:** the graph is declarative and testable; nodes are small closures over a `Deps` container.
- **Positive:** LangSmith tracing is available for free when enabled.
- **Negative:** adds a framework dependency and a learning curve; state must stay serializable.
- **Mitigation:** dependency injection keeps nodes free of framework-specific state; the
  whole graph runs offline against a deterministic fake LLM in CI.
