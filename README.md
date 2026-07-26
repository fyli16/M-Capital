# M Capital — Multi-Agent AI Investment Research Firm

A cloud-native platform where specialized AI analyst agents collaborate, debate, and
produce auditable investment recommendations.

> **Disclaimer:** M Capital produces *simulated research*. It is **not** financial advice and never auto-executes trades.

## Build steps

<!-- Built in reviewable increments. Current increment: **Database schema + shared contracts**. -->

| Increment | Scope | 
|---|---|
| 1 | Monorepo base + local DB stack |
| 2 | Shared contracts (agent I/O + API DTOs) | 
| 3 | SQLAlchemy models + pgvector | 
| 4 | Alembic initial migration | 
| 5 | TypeScript contract mirror | 
| 6 | ER diagram + docs | 
| 7 | agent-worker (LangGraph, 6 agents, debate, memory) | 
| 8 | Real data providers (Yahoo Finance + SEC EDGAR) | 
| 9 | Observability (OpenTelemetry + Grafana) | 
| 10 | api-gateway (FastAPI, JWT/RBAC, SSE, SQS) | 
| 11 | performance-worker (returns + agent scoring) | 
| 12 | web (Next.js dashboard: 6 views, live SSE/poll) | 
| 13 | infra (Terraform: ECS Fargate, RDS, Redis, SQS) + CI/CD | 

## Repository layout

```
M-capital/
├── docker-compose.yml        # Postgres+pgvector, Redis (local dev)
├── Makefile                  # dev entrypoints
├── packages/aegis_shared/    # SINGLE SOURCE OF TRUTH: Pydantic contracts + SQLAlchemy models
├── db/                       # Alembic config + migrations
├── web/lib/types/            # TypeScript mirror of contracts (frontend)
└── docs/architecture/        # ER diagram, ADRs, design notes
```

## Quick start (local)

Requires Docker. On Windows, run `make` targets from Git Bash / WSL, or run the
underlying commands shown in the [Makefile](Makefile) directly in PowerShell.

```bash
# 1. Start Postgres (pgvector) + Redis
make up

# 2. Install the shared package (editable) into your venv
make install

# 3. Apply the schema
make migrate

# 4. Export JSON Schemas (feeds frontend type generation)
make export-schemas
```

## Design docs

- [System architecture & tradeoffs](docs/architecture/README.md)
- [Data model & ER diagram](docs/architecture/data-model.md)
