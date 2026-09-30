.PHONY: install run run-local stop test test-unit test-integration lint typecheck migrate \
	new-module openapi e2e check

COMPOSE := docker compose --env-file .env -f deploy/docker-compose.yml
COMPOSE_LOCAL := $(COMPOSE) -f deploy/docker-compose.local.yml

install:
	cd backend && uv sync
	cd frontend && pnpm install

run:
	$(COMPOSE) up -d --build

run-local:
	$(COMPOSE_LOCAL) up -d --build

stop:
	$(COMPOSE_LOCAL) down

test: test-unit test-integration
	cd frontend && pnpm test

test-unit:
	cd backend && uv run pytest -m "not integration"

# Needs Docker (testcontainers), or TEST_DATABASE_URL pointing at a disposable database.
test-integration:
	cd backend && uv run pytest -m integration --cov=app --cov-report=term-missing

e2e:
	cd frontend && pnpm e2e

lint:
	cd backend && uv run ruff check . && uv run ruff format --check . && uv run lint-imports
	cd frontend && pnpm lint

typecheck:
	cd backend && uv run mypy --strict app tests conftest.py
	cd frontend && pnpm typecheck

migrate:
	$(COMPOSE) run --rm migrate

# Regenerate the API contract and the frontend client types from it.
openapi:
	cd backend && uv run python -m scripts.export_openapi
	cd frontend && pnpm api:types

new-module:
	@test -n "$(NAME)" || { echo "usage: make new-module NAME=x"; exit 1; }
	cd backend && uv run python -m scripts.new_module $(NAME)

check: lint typecheck test
