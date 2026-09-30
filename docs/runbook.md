# Runbook — running locally

Status: skeleton. M0 fills in the real commands as the stack is created.

## Prerequisites
- Docker + Docker Compose, Python 3.12 with `uv`, Node LTS with `pnpm`, `make`.

## First run
1. `cp .env.example .env` and set real local values (never commit `.env`).
2. `make install`
3. `make run` — starts Postgres (PostGIS + pgvector), Valkey, SeaweedFS, Keycloak, Caddy, API, worker, beat (defined in `deploy/docker-compose.yml`, created in M0).
4. `make migrate`

## Everyday
- `make test`, `make lint`, `make typecheck`
- New module: `make new-module NAME=x`

## Troubleshooting
- Add entries here as problems are found.
