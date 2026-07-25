"""initial schema

Revision ID: 0001_initial
Revises:
Create Date: 2026-07-25

Creates the full M Capital schema: users, research pipeline, debate, results,
performance tracking, and pgvector-backed memory. Enum-like columns use TEXT + CHECK.
"""
from __future__ import annotations

from alembic import op

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None

EMBEDDING_DIM = 1536


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector;")
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto;")

    # ---- users ----
    op.execute(
        """
        CREATE TABLE users (
            id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            email          VARCHAR(320) NOT NULL UNIQUE,
            hashed_password VARCHAR(255) NOT NULL,
            role           VARCHAR(32) NOT NULL DEFAULT 'analyst',
            created_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT ck_role CHECK (role IN ('viewer', 'analyst', 'admin'))
        );
        """
    )

    # ---- research_requests ----
    op.execute(
        """
        CREATE TABLE research_requests (
            id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id    UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            ticker     VARCHAR(12) NOT NULL,
            status     VARCHAR(16) NOT NULL DEFAULT 'queued',
            params     JSONB NOT NULL DEFAULT '{}'::jsonb,
            error      TEXT,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT ck_status CHECK
                (status IN ('queued','running','debating','complete','failed'))
        );
        CREATE INDEX ix_research_requests_ticker ON research_requests (ticker);
        CREATE INDEX ix_research_requests_status ON research_requests (status);
        CREATE INDEX ix_research_requests_user_created
            ON research_requests (user_id, created_at DESC);
        """
    )

    # ---- agent_runs ----
    op.execute(
        """
        CREATE TABLE agent_runs (
            id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            request_id UUID NOT NULL REFERENCES research_requests(id) ON DELETE CASCADE,
            agent_type VARCHAR(32) NOT NULL,
            status     VARCHAR(16) NOT NULL DEFAULT 'pending',
            tokens_in  INTEGER NOT NULL DEFAULT 0,
            tokens_out INTEGER NOT NULL DEFAULT 0,
            latency_ms INTEGER,
            cost_usd   DOUBLE PRECISION NOT NULL DEFAULT 0.0,
            error      TEXT,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT ck_agent_type CHECK
                (agent_type IN ('news','financial','quant','macro','risk','portfolio_manager')),
            CONSTRAINT ck_run_status CHECK
                (status IN ('pending','running','complete','failed','abstained')),
            CONSTRAINT uq_agent_run_per_request UNIQUE (request_id, agent_type)
        );
        CREATE INDEX ix_agent_runs_request ON agent_runs (request_id);
        """
    )

    # ---- agent_outputs ----
    op.execute(
        """
        CREATE TABLE agent_outputs (
            id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            run_id     UUID NOT NULL UNIQUE REFERENCES agent_runs(id) ON DELETE CASCADE,
            payload    JSONB NOT NULL,
            confidence DOUBLE PRECISION NOT NULL,
            sources    JSONB NOT NULL DEFAULT '[]'::jsonb,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT ck_output_conf CHECK (confidence >= 0 AND confidence <= 1)
        );
        """
    )

    # ---- debates ----
    op.execute(
        """
        CREATE TABLE debates (
            id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            request_id UUID NOT NULL UNIQUE REFERENCES research_requests(id) ON DELETE CASCADE,
            rounds     INTEGER NOT NULL DEFAULT 0,
            outcome    VARCHAR(16) NOT NULL DEFAULT 'no_conflict',
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT ck_outcome CHECK
                (outcome IN ('no_conflict','consensus','converged','max_rounds'))
        );
        """
    )

    # ---- debate_turns ----
    op.execute(
        """
        CREATE TABLE debate_turns (
            id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            debate_id  UUID NOT NULL REFERENCES debates(id) ON DELETE CASCADE,
            round      INTEGER NOT NULL,
            agent_type VARCHAR(32) NOT NULL,
            argument   TEXT NOT NULL,
            rebuts     VARCHAR(32),
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT ck_turn_agent_type CHECK
                (agent_type IN ('news','financial','quant','macro','risk','portfolio_manager'))
        );
        CREATE INDEX ix_debate_turns_debate_round ON debate_turns (debate_id, round);
        """
    )

    # ---- recommendations ----
    op.execute(
        """
        CREATE TABLE recommendations (
            id                 UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            request_id         UUID NOT NULL UNIQUE REFERENCES research_requests(id) ON DELETE CASCADE,
            ticker             VARCHAR(12) NOT NULL,
            action             VARCHAR(16) NOT NULL,
            confidence         DOUBLE PRECISION NOT NULL,
            rationale          TEXT NOT NULL,
            key_risks          JSONB NOT NULL DEFAULT '[]'::jsonb,
            supporting_factors JSONB NOT NULL DEFAULT '[]'::jsonb,
            created_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT ck_action CHECK
                (action IN ('strong_buy','buy','hold','sell','strong_sell')),
            CONSTRAINT ck_rec_conf CHECK (confidence >= 0 AND confidence <= 1)
        );
        CREATE INDEX ix_recommendations_ticker ON recommendations (ticker);
        CREATE INDEX ix_recommendations_created ON recommendations (created_at DESC);
        """
    )

    # ---- performance_tracking ----
    op.execute(
        """
        CREATE TABLE performance_tracking (
            id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            recommendation_id UUID NOT NULL REFERENCES recommendations(id) ON DELETE CASCADE,
            ret_30d           DOUBLE PRECISION,
            ret_60d           DOUBLE PRECISION,
            ret_90d           DOUBLE PRECISION,
            benchmark_ret_90d DOUBLE PRECISION,
            measured_at       TIMESTAMPTZ,
            created_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at        TIMESTAMPTZ NOT NULL DEFAULT now()
        );
        CREATE INDEX ix_perf_recommendation ON performance_tracking (recommendation_id);
        """
    )

    # ---- agent_contributions ----
    op.execute(
        """
        CREATE TABLE agent_contributions (
            id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            recommendation_id UUID NOT NULL REFERENCES recommendations(id) ON DELETE CASCADE,
            agent_type        VARCHAR(32) NOT NULL,
            confidence        DOUBLE PRECISION NOT NULL,
            supported         BOOLEAN NOT NULL,
            was_correct       BOOLEAN,
            created_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT ck_contribution_agent_type CHECK
                (agent_type IN ('news','financial','quant','macro','risk','portfolio_manager')),
            CONSTRAINT uq_contribution_per_agent UNIQUE (recommendation_id, agent_type)
        );
        CREATE INDEX ix_contrib_agent ON agent_contributions (agent_type);
        """
    )

    # ---- memories ----
    op.execute(
        """
        CREATE TABLE memories (
            id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            request_id UUID REFERENCES research_requests(id) ON DELETE SET NULL,
            ticker     VARCHAR(12) NOT NULL,
            summary    TEXT NOT NULL,
            content    JSONB NOT NULL DEFAULT '{}'::jsonb,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        );
        CREATE INDEX ix_memories_ticker ON memories (ticker);
        """
    )

    # ---- embeddings (pgvector + HNSW) ----
    op.execute(
        f"""
        CREATE TABLE embeddings (
            id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            memory_id  UUID NOT NULL UNIQUE REFERENCES memories(id) ON DELETE CASCADE,
            model      VARCHAR(64) NOT NULL,
            embedding  vector({EMBEDDING_DIM}) NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        );
        """
    )
    # HNSW gives strong recall/latency for our read-heavy retrieval pattern.
    # cosine distance matches OpenAI embedding similarity convention.
    op.execute(
        """
        CREATE INDEX ix_embeddings_hnsw
            ON embeddings USING hnsw (embedding vector_cosine_ops)
            WITH (m = 16, ef_construction = 64);
        """
    )


def downgrade() -> None:
    for table in (
        "embeddings",
        "memories",
        "agent_contributions",
        "performance_tracking",
        "recommendations",
        "debate_turns",
        "debates",
        "agent_outputs",
        "agent_runs",
        "research_requests",
        "users",
    ):
        op.execute(f"DROP TABLE IF EXISTS {table} CASCADE;")
