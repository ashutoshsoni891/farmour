.PHONY: install run test lint typecheck migrate new-module

# Targets are stubs until M0 creates backend/, frontend/ and deploy/.
# Each target fails loudly if its prerequisite does not exist yet.

install:
	@test -d backend && (cd backend && uv sync) || echo "backend/ not created yet (M0)"
	@test -d frontend && (cd frontend && pnpm install) || echo "frontend/ not created yet (M0)"

run:
	@test -f deploy/docker-compose.yml || { echo "deploy/docker-compose.yml not created yet (M0)"; exit 1; }
	docker compose -f deploy/docker-compose.yml up

test:
	@test -f backend/pyproject.toml || { echo "backend not created yet (M0)"; exit 1; }
	cd backend && uv run pytest
	@test -d frontend && (cd frontend && pnpm test) || true

lint:
	@test -f backend/pyproject.toml || { echo "backend not created yet (M0)"; exit 1; }
	cd backend && uv run ruff check . && uv run ruff format --check . && uv run lint-imports
	@test -d frontend && (cd frontend && pnpm lint) || true

typecheck:
	@test -f backend/pyproject.toml || { echo "backend not created yet (M0)"; exit 1; }
	cd backend && uv run mypy --strict app
	@test -d frontend && (cd frontend && pnpm exec tsc --noEmit) || true

migrate:
	@test -f backend/pyproject.toml || { echo "backend not created yet (M0)"; exit 1; }
	cd backend && uv run alembic upgrade head

new-module:
	@test -n "$(NAME)" || { echo "usage: make new-module NAME=x"; exit 1; }
	@echo "Scaffold script is added in M0; until then follow .claude/skills/new-module/SKILL.md"; exit 1
