# ADR 0001 — Monorepo with a shared contracts package

**Status:** Accepted

## Context

The platform spans a FastAPI gateway, multiple Python workers, and a TypeScript
frontend. These components communicate through data shapes (agent outputs, API DTOs,
DB models). If each service owned its own copy of these types, they would drift, and
a change to one contract would silently break consumers.

## Decision

Use a **monorepo** with a single source-of-truth package, `packages/aegis_shared`,
containing the Pydantic contracts and SQLAlchemy models. All Python services depend
on it; the frontend consumes a TypeScript mirror generated from the same contracts
(via exported JSON Schema). One pull request can change a contract, its producers,
its consumers, and the infrastructure atomically.

## Consequences

- **Positive:** no cross-service type drift; atomic changes; one CI pipeline; shared tooling.
- **Positive:** contract changes are visible and reviewable in a single diff.
- **Negative:** the repo is larger; services are coupled to the shared package version.
- **Mitigation:** the shared package is deliberately thin (contracts + models only) and
  imports no service code, keeping the coupling one-directional.
