# Architecture Decision Records

Short, immutable records of the significant technical decisions behind Aegis Capital.
Each ADR captures the context, the decision, and its consequences at the time it was made.

| # | Decision | Status |
|---|---|---|
| [0001](0001-monorepo.md) | Monorepo with shared contracts package | Accepted |
| [0002](0002-langgraph-orchestration.md) | LangGraph for agent orchestration | Accepted |
| [0003](0003-text-check-enums.md) | `TEXT + CHECK` over native Postgres enums | Accepted |
| [0004](0004-event-driven-sqs.md) | Event-driven execution via SQS | Accepted |
| [0005](0005-ports-and-adapters.md) | Ports & adapters for LLM, data, queue | Accepted |
| [0006](0006-pm-narrates-math-decides.md) | Deterministic decision, LLM-authored narrative | Accepted |
| [0007](0007-good-dissent-scoring.md) | Reward good dissent in agent scoring | Accepted |
| [0008](0008-ecs-fargate.md) | AWS ECS Fargate deployment | Accepted |
| [0009](0009-offline-fakes-testing.md) | Deterministic fakes for offline testing | Accepted |

## Format

Each ADR follows: **Status · Context · Decision · Consequences**. ADRs are append-only;
to reverse a decision, add a new ADR that supersedes the old one.
