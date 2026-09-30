# Runbook — running locally

## Prerequisites
- Docker with Compose v2. On Windows + WSL2: Docker Desktop → Settings → Resources →
  WSL integration → enable for your distro.
- Python 3.12 via `uv` (`uv python install 3.12`), Node 22 (`nvm use` in `frontend/`),
  pnpm (`corepack enable pnpm`), `make`.

## First run
1. `cp .env.example .env` and replace every `change-me` (use long random values).
2. `make install`
3. `make run-local` — builds and starts Postgres (PostGIS + pgvector), Valkey, SeaweedFS,
   Keycloak, migrations, API, worker, beat and Caddy. First start of Keycloak takes ~1 minute.
4. Open http://localhost → "Sign in or create account" → register an owner in Keycloak.
5. Make yourself admin (after logging in once):
   `docker compose --env-file .env -f deploy/docker-compose.yml exec api python -m app.cli make-admin you@example.com`

`make run-local` also binds Postgres to 127.0.0.1:5432 (for `.mcp.json`) and the Keycloak
admin console to http://127.0.0.1:8081/auth/admin (user `KEYCLOAK_ADMIN_USER`). Neither is
reachable through Caddy.

## Everyday
- `make check` — lint, types, all tests (integration tests start a Postgres container).
- `make test-unit` — fast tests without Docker. `make e2e` — Playwright at mobile width.
- `make openapi` — after changing API schemas: regenerate `backend/openapi.json` and the
  frontend client types (CI fails if they are stale).
- `make new-module NAME=x` — scaffold a module (see `.claude/skills/new-module`).
- Frontend dev server with hot reload: `cd frontend && pnpm dev` (proxies /api and /auth to
  the stack on http://localhost).

## Staging deploy
When CI passes on `main`, the deploy workflow builds images, scans them with Trivy and pushes to GHCR
(`.github/workflows/deploy-staging.yml`). The deploy job runs when the repository variable
`STAGING_ENABLED=true` and secrets `STAGING_HOST`, `STAGING_USER`, `STAGING_SSH_KEY`,
`STAGING_SSH_KNOWN_HOSTS` are set. The server needs Docker, a `farm/` directory with its own
`.env` (`ENV=staging`, `SITE_ADDRESS=<domain>`, `APP_BASE_URL=https://<domain>`), ports
80/443 open and nothing else.

## Troubleshooting
- Hindi shows as boxes: the bundled font failed to load; check the network tab for
  `noto-sans-devanagari-*.woff2`.
- Playwright on WSL without sudo: extract `libnss3 libnspr4 libasound2t64` with
  `apt-get download` + `dpkg -x` and point `LD_LIBRARY_PATH` at them.
- `SETTING_MISSING` errors: migrations not applied (`make migrate`).
