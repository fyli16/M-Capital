# M Capital agent-worker. Build context = repository root:
#   docker build -f services/agent-worker/Dockerfile -t aegis/agent-worker .
FROM python:3.12-slim AS base

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /srv

# Shared contracts/models first (better layer caching).
COPY packages/aegis_shared /srv/packages/aegis_shared
RUN pip install /srv/packages/aegis_shared

COPY services/agent-worker/pyproject.toml /srv/services/agent-worker/pyproject.toml
COPY services/agent-worker/app /srv/services/agent-worker/app
RUN pip install "/srv/services/agent-worker[openai,aws]"

# Run as non-root.
RUN useradd --create-home --uid 10001 aegis
USER aegis

WORKDIR /srv/services/agent-worker
CMD ["python", "-m", "app", "consume"]
