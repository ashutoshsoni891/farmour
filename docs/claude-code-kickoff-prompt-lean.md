# Claude Code prompts — Farm platform MVP (lean, Pro-plan friendly, no test focus)

## Before you paste anything

1. Create an empty GitHub repo (e.g. `farm-platform`) and clone it.
2. In the Claude doc, open the **"MVP technical spec"** tab, export as **Markdown**, and split it into one file per numbered section under `docs/spec/` (e.g. `05-data-model.md`, `07-design-engine.md`) plus a one-page `docs/spec/00-index.md` listing each file and one line on what it covers. (Splitting means Claude reads only what a task needs instead of the whole spec every session.)
3. Open the repo in Claude Code. Paste **Prompt 1** once, then **Prompt 2** per slice of work.

---

## Prompt 1 — Kickoff (paste once)

```
You are the lead engineer on a farm planning platform for India (Malwa / Indore first). The build spec is split into sections in docs/spec/; start with docs/spec/00-index.md and read ONLY the sections a task needs. Never read the whole spec at once.

## Goal
Ship a working MVP fast. Features first. We are NOT writing tests, CI pipelines, security scans, evals, coverage gates, monitoring stacks or backup automation now; those are post-MVP. Do not create them, and do not mention them as blockers.

## Build scope (spec section 1)
Plan (location + boundary + site intelligence + design engine), weekly Hindi tasks to the caretaker on Telegram, logs, profit view, text AI helper, shopping list, basic legal pages. Everything marked "post-MVP" in the spec is out.

## Rules (keep these, they are cheap and prevent rewrites)
1. Stack is fixed by spec section 4: FastAPI, Postgres + PostGIS + pgvector, Celery + Valkey, SeaweedFS, Keycloak, React PWA, Docker Compose. No other dependencies without asking. Never MinIO. Never hand-write password or token handling.
2. Outside services go behind small adapters in app/adapters/ (LLM, storage, messaging channel, weather, geocoding, site data sources).
3. Keep modules separate: each module owns its tables and talks to others through its service functions.
4. Agronomy facts (spacing, seasons, yields, remedies, prices) come only from crop library data, never invented in code. Seed entries as status "draft".
5. Numbers from the spec (widths, thresholds, limits) live in the settings table or library, not hard-coded.
6. Money in integer paise; geometry stored in EPSG:4326 and computed in EPSG:32643; time stored in UTC; every user-facing string is an i18n key with en and hi.
7. Secrets only in .env (gitignored). Farm access checked through one permission dependency; a caretaker never sees money unless allowed.
8. When the spec is silent, pick the simplest option and add one line to docs/decisions.md. Ask me only if the choice is expensive to undo.

## First task (no product code yet)
Create only this, then stop:
- CLAUDE.md under 100 lines: purpose in 3 lines, the rules above, run/lint/migrate commands, "read docs/spec/00-index.md and only the needed sections".
- A Makefile with up, down, migrate, run, lint.
- .gitignore, .env.example (all variables from spec section 4, dummy values), docs/decisions.md (empty).
- docker-compose.yml for postgres+postgis+pgvector, valkey, seaweedfs, keycloak, caddy, and the api service skeleton.
Show me the file tree and wait.

## How we work
- Small slices: one clear feature per session (for example "farms and parcels tables + migration + create/read endpoints").
- For anything bigger than a small change, use plan mode first: list files and tables to touch, wait for my OK.
- Run the app yourself to confirm it works (start it, hit the endpoint or open the page). No separate test suite.
- Short report at the end: what works, what I should try by hand, and the next slice. Keep it under 10 lines.
- Keep context small: don't re-read files you just wrote, don't dump long outputs.
```

---

## Prompt 2 — Each slice of work

```
Work on: <slice, e.g. "M0: docker compose stack up with Keycloak login working">.

Read docs/spec/00-index.md and only the sections this slice needs. Stay inside the MVP scope. If it's more than a small change, give me a short plan first. Build it, run it to confirm it works, and give me a short report (what works, what to try by hand, next slice).
```

### Suggested slices (replaces the heavy milestone workflow)

| # | Slice | Done when |
|---|---|---|
| M0a | Compose stack up (Postgres, Valkey, SeaweedFS, Keycloak, Caddy), API health endpoint | `make up` works and health responds |
| M0b | Keycloak login for owners; caretaker invite-link login; roles; i18n scaffold | You can log in as owner and as a caretaker |
| M0c | Module scaffold, adapter interfaces, outbox table, settings table | App starts with empty modules wired |
| M1 | Crop library tables, admin screen, seed ~60 crops + recipes as draft | Crops visible and editable in admin |
| M2a | Parcel: setup wizard, map drawing, enter-measurements | Draw or type a plot and see area |
| M2b | Site intelligence adapters + "We found for your land" card | Card fills for an Indore location |
| M3 | Design engine and plan view | A plan appears for your 800 sq ft plot |
| M4 | Planner, tasks, shopping list | Weekly tasks and shopping list appear |
| M5 | Telegram bot: invite, daily tasks, done/not-done, text logging | Caretaker completes a day by Telegram |
| M6 | Logs, profit, plan vs actual | Money screen shows real numbers |
| M7 | AI helper (text) + terms/privacy/disclaimer + export/delete | Questions answered from the library |
| M8 | Run your own plot and 5-10 users | Real use |

### Handy follow-ups

- **Keep it small:** `Stop. Summarise what exists in 5 lines, then do only the next slice.`
- **Context getting long:** `/compact keep decisions and current slice status` or `/clear` and restart the slice with Prompt 2.
- **Something broke:** `Reproduce it, fix the root cause with the smallest change, confirm it runs.`
- **Later, when the MVP works:** `Now add tests for the design engine and profit calculations only.`
