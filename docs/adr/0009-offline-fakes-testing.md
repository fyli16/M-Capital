# ADR 0009 — Deterministic fakes for offline testing

**Status:** Accepted

## Context

The system's behavior depends on an LLM and external data feeds, which are
non-deterministic, cost money, require keys, and may be blocked on corporate networks.
Tests and CI must nonetheless be fast, free, deterministic, and network-free — while the
agent pipeline is exactly the part most worth testing.

## Decision

Provide **deterministic fakes** behind the ports from ADR 0005:

- `FakeLLM` fabricates schema-valid outputs seeded by the prompt hash, so the same input
  yields the same output. It is the default provider.
- Synthetic data providers produce ticker-seeded, reproducible market/news/filings data.
- Services expose a repository/service layer that tests override with in-memory fakes,
  so the full HTTP surface and the graph are exercised without a database.

An **evaluation harness** (`python -m app.eval`) runs the pipeline over a golden dataset
and asserts structural/behavioral invariants plus determinism (and optional LLM-as-judge),
acting as a CI regression gate.

## Consequences

- **Positive:** CI needs no keys, network, or Postgres; tests are fast and deterministic.
- **Positive:** the eval gate catches pipeline regressions; the same fakes power local dev.
- **Negative:** fakes can mask integration issues that only real providers surface.
- **Mitigation:** an end-to-end compose stack (real Postgres/Redis/LocalStack SQS) covers
  the integration seams; live-provider paths degrade to synthetic and are exercised manually.
