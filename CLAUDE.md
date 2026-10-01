# Farmour — farm planning platform (MVP)

Farm planning platform for India (start: Malwa / Indore, MP). Owner draws land → site intelligence → deterministic design engine → weekly Hindi tasks to the caretaker on Telegram → logs and profit.
Spec: `docs/spec/` (index: `00-index.md`) is the source of truth. **Section 16 is binding.** Build milestones in section 15 order (M0 → M8). Anything marked "post-MVP" is NOT built.

## Rules (short form)
1. Modular monolith (§16): every module has `api.py service.py schemas.py repository.py events.py tests/` + README. No module touches another module's tables; cross-module calls go via `service.py` or outbox events. Outside services only via `backend/app/adapters/` (interface + impl + fake + registry + config).
2. Stack fixed by §4 (open source, self-hosted, Docker Compose). New dependency must pass §4 selection rules. Never MinIO. Never hand-write password/token handling — Keycloak.
3. Agronomy facts (spacing, seasons, yields, remedies, prices) come ONLY from the crop library. Never invent them in code, prompts, seeds or tests. Seed entries are `status: draft` with a `TODO(agronomist)`.
4. Every number the spec gives is a config value (`settings` table or library), not a constant.
5. Money = integer paise. Geometry stored EPSG:4326, computed EPSG:32643. Time stored UTC, scheduled Asia/Kolkata. User-facing strings are i18n keys (`en`, `hi`).
6. Security from commit 1: secrets only in `.env` (gitignored); parameterised queries; one `require_farm_role` dependency for row-level checks; caretaker never sees money unless `caretaker_sees_money`.
7. Spec silent → simplest option respecting §16, log in `docs/decisions.md`. Spec ambiguous AND costly to reverse → stop and ask.

## Commands (Makefile)
- `make install` — uv sync (backend) + pnpm install (frontend; Node 22 via `nvm use`)
- `make run-local` — full stack with Docker Compose (see docs/runbook.md); `make stop`
- `make test` — backend unit + integration (Docker) + frontend unit; `make test-unit` without Docker
- `make e2e` — Playwright at mobile width
- `make lint` — ruff + import-linter + eslint/prettier
- `make typecheck` — mypy --strict + tsc
- `make migrate` — alembic upgrade head (in Compose)
- `make openapi` — regenerate API contract and frontend client types after API changes
- `make new-module NAME=x` — scaffold a module (skill `new-module`)

## Lean mode (docs/claude-code-kickoff-prompt-lean.md)
Features first. Do NOT write tests, CI, security scans, evals, coverage gates, monitoring or
backup automation now (post-MVP), and don't call them blockers. Verify by running the app
(start it, hit the endpoint or open the page). Small slices; plan mode only for bigger work.
Read `docs/spec/00-index.md` and only the sections a task needs. Don't re-read files you just
wrote. Reports: what works, what to try by hand, next slice, under 10 lines.

## Definition of done for a slice
- Runs (you started it and it works); module boundaries kept (`make lint` import-linter)
- Migration follows expand → contract; new outside service only as an adapter
- `docs/decisions.md` gets one line for any choice the spec was silent on

## Layout
`backend/` (FastAPI; `app/{api,core,adapters,modules,jobs,db}`, `seeds/`, `tests/`), `frontend/` (React+TS PWA), `deploy/` (Compose, Caddy, backup), `docs/`. Path rules: `.claude/rules/`. Tooling: `uv` (Python), `pnpm` (frontend).
