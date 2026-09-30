# Farmour — farm planning platform (MVP)

Farm planning platform for India (start: Malwa / Indore, MP). Owner draws land → site intelligence → deterministic design engine → weekly Hindi tasks to the caretaker on Telegram → logs and profit.
Spec: `docs/spec/MVP-technical-spec.md` is the single source of truth. **Section 16 is binding.** Build milestones in section 15 order (M0 → M8). Anything marked "post-MVP" is NOT built.

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

## Definition of done for any change (§16)
- [ ] Stays inside its module boundary (import-linter passes)
- [ ] New outside dependency only as an adapter, passing §4 selection rules
- [ ] Tests added; golden tests / AI evals pass where relevant
- [ ] Migration follows expand → migrate → contract; API change additive or versioned
- [ ] Behind a feature flag if user-facing and risky
- [ ] Module README and `docs/decisions.md` updated when behaviour/structure changes

## Milestone workflow
1. Plan mode first: read the milestone (§15) and every section it touches; list files, tables, endpoints, tests, risks, questions. Wait for approval.
2. Small, green commits with clear messages.
3. Tests via `test-writer`; design engine always gets golden + property tests.
4. Run `architecture-reviewer` and `security-reviewer`; fix or justify.
5. Run `milestone-check` skill; done only when every item passes.
6. Update `docs/decisions.md`, module READMEs, `docs/runbook.md`.
7. Report: built, test results, spec deviations, decisions, open questions, exact next step.

## Quality bar
- Verify by running: app and tests; UI at mobile width in Hindi and English.
- Never mark done what you haven't run. Fix code, not tests (unless the test is wrong — say so).
- Boring, well-documented solutions. Exceeding milestone scope → stop and ask.

## Layout
`backend/` (FastAPI; `app/{api,core,adapters,modules,jobs,db}`, `seeds/`, `tests/`), `frontend/` (React+TS PWA), `deploy/` (Compose, Caddy, backup), `docs/`. Path rules: `.claude/rules/`. Tooling: `uv` (Python), `pnpm` (frontend).
