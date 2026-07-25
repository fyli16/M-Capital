# M Capital API gateway. Build context = repository root:
#   docker build -f services/api-gateway/Dockerfile -t aegis/api-gateway .
FROM python:3.12-slim AS base

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /srv

COPY packages/aegis_shared /srv/packages/aegis_shared
RUN pip install /srv/packages/aegis_shared

COPY services/api-gateway/pyproject.toml /srv/services/api-gateway/pyproject.toml
COPY services/api-gateway/app /srv/services/api-gateway/app
RUN pip install "/srv/services/api-gateway[redis,aws]"

RUN useradd --create-home --uid 10002 aegis
USER aegis

WORKDIR /srv/services/api-gateway
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
