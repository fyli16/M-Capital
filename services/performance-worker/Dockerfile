# Aegis Capital performance-worker (scheduled task). Build context = repo root:
#   docker build -f services/performance-worker/Dockerfile -t aegis/performance-worker .
FROM python:3.12-slim AS base

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /srv

COPY packages/aegis_shared /srv/packages/aegis_shared
RUN pip install /srv/packages/aegis_shared

COPY services/performance-worker/pyproject.toml /srv/services/performance-worker/pyproject.toml
COPY services/performance-worker/app /srv/services/performance-worker/app
RUN pip install "/srv/services/performance-worker[live]"

RUN useradd --create-home --uid 10003 aegis
USER aegis

WORKDIR /srv/services/performance-worker
# Invoked on a schedule; the task exits after one measurement pass.
CMD ["python", "-m", "app", "run"]
