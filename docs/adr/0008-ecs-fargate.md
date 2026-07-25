# ADR 0008 — AWS ECS Fargate deployment

**Status:** Accepted

## Context

The platform is three long-running services (API gateway, agent worker, performance
worker) plus stateful backing stores (Postgres+pgvector, Redis, SQS). We need
horizontal scaling — especially of the workers on queue depth — without operating a
Kubernetes control plane.

## Decision

Deploy on **AWS ECS Fargate**, provisioned with Terraform (single-root, per-env tfvars):

- **api-gateway** behind an ALB, autoscaled on CPU.
- **agent-worker** with no load balancer, autoscaled on **SQS depth**.
- **performance-worker** as an **EventBridge-scheduled** Fargate task.
- **RDS Postgres** (pgvector), **ElastiCache Redis**, **SQS + DLQ**, **Secrets Manager**.
- Least-privilege IAM task roles; CloudWatch logs; deployment circuit-breaker with rollback.
- DB migrations run as a dedicated one-off Fargate task in CD before new deployments roll out.

## Consequences

- **Positive:** no cluster to manage; scales to zero-ish for the worker fleet; native AWS integration.
- **Positive:** each service scales on its true bottleneck; workers track the queue.
- **Negative:** AWS-specific; Fargate per-task cost > EC2 at steady high utilization.
- **Negative:** cold starts on scale-out; the LLM provider rate limit is the real ceiling, not compute.
- **Mitigation:** the queue abstraction (ADR 0005) keeps a future move to another cloud feasible.
