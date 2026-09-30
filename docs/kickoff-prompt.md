# Claude Code prompts — Farm planning platform MVP

## Before you paste anything

1. Create an empty GitHub repo (e.g. `farm-platform`) and clone it.
2. In the Claude doc, open the **"MVP technical spec"** tab and export it as **Markdown**. Save it in the repo as `docs/spec/MVP-technical-spec.md`.
3. Open the repo folder in Claude Code (terminal, VS Code or desktop).
4. Paste **Prompt 1** once. After it finishes, use **Prompt 2** for every milestone.

---

## Prompt 1 — Kickoff (paste once)

```
You are the lead engineer on a new product: a farm planning platform for India (starting with Malwa / Indore, Madhya Pradesh). The complete build spec is in docs/spec/MVP-technical-spec.md. That spec is the single source of truth. Read all of it before doing anything else.

## What we are building
A lean MVP (spec section 1): the owner pins a location and draws the land; site intelligence auto-fills soil, climate, water stress, mandi prices and distances (section 17); a deterministic design engine returns zones, beds and crops per layer (section 7); a planner creates weekly Hindi tasks sent to the caretaker on Telegram (sections 8, 10); logs and a profit view (section 9); a grounded AI helper (section 11); a seasonal shopping list; legal basics. Everything marked "post-MVP" in the spec must NOT be built.

## Non-negotiable rules
1. Section 16 (extensibility, scaling and change rules) is binding: modular monolith, each module in the standard shape, no module touches another module's tables, all outside services behind adapters in app/adapters/, events via the outbox table.
2. Stack is fixed by section 4 (open source, self-hosted, Docker Compose). Do not add a dependency that fails section 4's selection rules. Never use MinIO. Never hand-write password or token handling; use Keycloak.
3. Agronomy facts (spacing, seasons, yields, remedies, prices) come ONLY from the crop library data. Never invent them in code, prompts, seeds or tests. Where seed data needs values, mark entries status "draft" and add a TODO for agronomist review.
4. Every number the spec gives (thresholds, widths, limits) is a config value in the settings table or library, not a hard-coded constant.
5. Money in integer paise; geometry stored in EPSG:4326 and computed in EPSG:32643; time stored in UTC and scheduled in Asia/Kolkata; every user-facing string is an i18n key with en and hi.
6. Security from the first commit: secrets only in .env (gitignored), parameterised queries, row-level farm permission checks via one dependency, a caretaker must never see money unless allowed.
7. When the spec is silent, choose the simplest option that respects section 16 and record it in docs/decisions.md. When the spec is ambiguous AND the choice is expensive to reverse, stop and ask me.

## Your first task: set up the working environment (do not write product code yet)
Use plan mode. Propose, then wait for my approval, then create:

a) CLAUDE.md at the repo root (keep it under ~120 lines): project purpose in 3 lines; "follow docs/spec/, section 16 is binding, build milestones in section 15 order"; the rules above in short form; exact commands for install, run, test, lint, typecheck, migrate (Makefile targets); definition of done for any change (section 16).

b) .claude/rules/ with path-specific rules:
   - backend.md (applies to backend/**): module shape, adapters, Alembic expand -> contract, Pydantic v2, async SQLAlchemy 2, mypy strict, error format from section 12.
   - engine.md (applies to backend/app/modules/layout/**): deterministic, rule-based, library-driven; UTM projection; golden and property tests required for every change; bump engine_version.
   - frontend.md (applies to frontend/**): React + TS strict, PWA offline queue, i18n keys only, 16px min text, 44px touch targets, Indian number format.

c) Skills in .claude/skills/ (each a SKILL.md with clear "when to use" description and steps):
   - new-module: scaffold a module in the section 16 shape (api, service, schemas, repository, events, tests, README) and register it.
   - add-adapter: interface + implementation + fake + registry entry + config switch + tests.
   - write-migration: Alembic migration following expand -> migrate -> contract; never drop/rename in the same release.
   - add-crop: add or edit a crop library entry with all required fields from section 6, status draft, no invented values.
   - milestone-check: verify a milestone's definition of done from section 15 plus the section 16 checklist; run all tests; report pass/fail per item.

d) Subagents in .claude/agents/:
   - architecture-reviewer (read-only): checks changes against section 16, section 4 selection rules and the spec; reports violations with file and line.
   - security-reviewer (read-only): auth, farm permissions, money visibility, secrets, input validation, OWASP basics.
   - geo-engine: design engine specialist (Shapely, pyproj, PostGIS, golden and property tests).
   - test-writer: writes unit, integration, golden and property tests for new code.

e) .claude/settings.json:
   - permissions: allow make, pytest, ruff, mypy, npm/pnpm test and lint, docker compose, alembic, git (no force push); deny reading or editing .env and any file under secrets/.
   - hooks: after file edits, run ruff format/fix on changed Python files and prettier on changed TS files; before edits, block writes to .env files and to Alembic migrations already applied (list tracked in migrations/APPLIED).

f) .mcp.json with only: GitHub, PostgreSQL (read-only role on the local dev database). Explain any other server before adding it.

g) docs/decisions.md (empty template), docs/runbook.md (how to run locally), .gitignore, .env.example with every variable from section 4 and dummy values.

After creating these, show me the file tree and a one-paragraph summary, then stop.

## How we work on every milestone after setup
1. Plan mode first: read the milestone in section 15 and every section it touches; list files to create or change, tables, endpoints, tests, risks and open questions. Wait for my approval.
2. Implement in small, reviewable commits with clear messages. Keep each commit green (tests pass).
3. Tests: use test-writer; the design engine always gets golden and property tests.
4. Review: run architecture-reviewer and security-reviewer; fix everything they flag or explain why not.
5. Run milestone-check. Only call the milestone done when every item passes.
6. Update docs/decisions.md, module READMEs and docs/runbook.md.
7. Finish with a short report: what was built, test results, deviations from spec, decisions made, open questions for me, and the exact next step.

## Quality bar
- Verify your own work: run the app and tests; for UI, open it in the browser at mobile width in Hindi and English.
- Never mark something done that you haven't run.
- If a test is hard to make pass, fix the code, not the test, unless the test is wrong; say which.
- Prefer boring, well-documented solutions over clever ones.
- If you are about to exceed the milestone scope, stop and ask.
```

---

## Prompt 2 — Each milestone (change the milestone number)

```
Start milestone M0 from docs/spec/MVP-technical-spec.md section 15.

Follow the milestone workflow in CLAUDE.md: plan mode first, read every spec section this milestone touches, then give me the plan (files, tables, endpoints, tests, risks, questions) and wait for approval. Stay strictly inside this milestone's scope and the MVP scope in section 1. Finish with milestone-check and the standard report.
```

Milestone order: M0 foundation → M1 crop library (can run in a parallel worktree with M2) → M2 parcel + site intelligence → M3 design engine → M4 planner, tasks, shopping list → M5 Telegram → M6 records and money → M7 AI helper + legal → M8 beta.

---

## Useful follow-up prompts

- **Review before merge:** `Run architecture-reviewer and security-reviewer on the changes since main, then /code-review. Fix what they find and summarise.`
- **Stuck or drifting:** `Stop. Re-read section 16 and this milestone's definition of done. List where the current work deviates, then propose the smallest fix.`
- **Spec change:** `I've updated docs/spec/MVP-technical-spec.md. Diff it against what's built, list what must change, and plan it as a small milestone.`
- **Parallel work:** `Create a worktree for M1 (crop library) and work there while M2 continues in main.`
