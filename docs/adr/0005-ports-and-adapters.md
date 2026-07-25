# ADR 0005 — Ports & adapters for LLM, data, and queue

**Status:** Accepted

## Context

The system depends on volatile, swappable externals: LLM providers (OpenAI, Claude,
Bedrock), market/news/filings data (Yahoo Finance, SEC EDGAR, licensed feeds), and a
message broker (SQS, Service Bus, Pub/Sub). Hard-coding any vendor makes the system
brittle, hard to test, and hard to run offline.

## Decision

Define narrow **ports** (protocols) for each external and program only against them:

- `LLMClient` — `structured()` + `embed()`; adapters: `FakeLLM`, `OpenAIClient`.
- Data providers — `MarketDataProvider` / `NewsProvider` / `FilingsProvider`; adapters:
  synthetic (default), Yahoo, EDGAR — each live source wrapped with a synthetic fallback.
- `Queue` — `enqueue()`; adapters: `InMemoryQueue`, `SqsQueue`.

## Consequences

- **Positive:** vendors are swappable; the whole platform runs offline via fakes.
- **Positive:** deterministic tests and CI with no keys or network.
- **Positive:** flaky live feeds degrade gracefully instead of failing a run.
- **Negative:** an abstraction tax and a lowest-common-denominator feature set.
- **Trade-off accepted:** portability and testability outweigh access to provider-specific extras.
