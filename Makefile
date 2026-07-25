# M Capital — developer entrypoints.
# On Windows without `make`, run the commands shown here directly in PowerShell.

DB_URL ?= postgresql+psycopg://aegis:aegis@localhost:5432/aegis

.PHONY: up down logs install migrate revision downgrade export-schemas psql clean e2e e2e-down

up:                     ## Start Postgres (pgvector) + Redis
	docker compose up -d

down:                   ## Stop containers
	docker compose down

logs:                   ## Tail container logs
	docker compose logs -f

install:                ## Install shared package (editable) + tooling
	pip install -e packages/aegis_shared[dev]

migrate:                ## Apply all migrations
	cd db && alembic upgrade head

revision:               ## Autogenerate a new migration: make revision m="message"
	cd db && alembic revision --autogenerate -m "$(m)"

downgrade:              ## Roll back one migration
	cd db && alembic downgrade -1

export-schemas:         ## Emit JSON Schemas from Pydantic contracts
	python packages/aegis_shared/scripts/export_schemas.py

psql:                   ## Open a psql shell
	docker exec -it aegis-postgres psql -U aegis -d aegis

clean:                  ## Stop and delete volumes (DESTRUCTIVE)
	docker compose down -v

e2e:                    ## Bring up the full stack and run end-to-end tests
	docker compose -f tests/e2e/docker-compose.e2e.yml up --build -d
	pip install -r tests/e2e/requirements.txt
	pytest tests/e2e -v

e2e-down:               ## Tear down the e2e stack
	docker compose -f tests/e2e/docker-compose.e2e.yml down -v
