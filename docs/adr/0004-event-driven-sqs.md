# ADR 0004 — Event-driven execution via SQS

**Status:** Accepted

## Context

An analysis fans out five LLM-driven agents plus a debate — seconds to minutes of
I/O-bound work. Holding an HTTP connection open for the duration does not scale to the
target of 1000+ concurrent analyses, and couples request throughput to worker capacity.

## Decision

The gateway **enqueues** a job to SQS and immediately returns `202 Accepted` with a
`stream_url`. A separate worker pool consumes the queue, runs the LangGraph pipeline,
and persists results. Clients receive progress via SSE (polling now; Redis pub/sub
fast-path planned). Workers autoscale on **queue depth**. A dead-letter queue with a
redrive policy captures poison messages; idempotency keys (Redis `SET NX`) prevent
double-processing on redelivery.

## Consequences

- **Positive:** request throughput decouples from processing capacity; natural backpressure.
- **Positive:** worker crashes are recoverable (message reappears after visibility timeout).
- **Negative:** eventual consistency; the client must poll/subscribe rather than block.
- **Negative:** adds a broker and DLQ operations (replay tooling) to run.
- **Abstraction:** the queue sits behind a `Queue` port so SQS can be swapped for Azure
  Service Bus or Pub/Sub (see ADR 0005).
