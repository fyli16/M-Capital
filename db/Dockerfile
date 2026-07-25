# Aegis Capital DB migrator. Build context = repository root:
#   docker build -f db/Dockerfile -t aegis/migrate .
# Runs `alembic upgrade head` against $DATABASE_URL, then exits.
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /srv

COPY packages/aegis_shared /srv/packages/aegis_shared
RUN pip install /srv/packages/aegis_shared "alembic>=1.13" "psycopg[binary]>=3.1"

COPY db /srv/db
WORKDIR /srv/db

CMD ["alembic", "upgrade", "head"]
