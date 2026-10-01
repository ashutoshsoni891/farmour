# Project status

Last updated: 2026-10-02. Source of truth for scope: `docs/spec/` (milestones in `15-build-order-and-open-questions.md`).
Everything below runs on the local Docker stack. Nothing is pushed to GitHub yet (see "Blockers").

## Milestones

| # | Milestone | State | What exists | What is missing |
|---|---|---|---|---|
| M0 | Foundation | Built, local | Compose stack (Postgres+PostGIS+pgvector, Valkey, SeaweedFS, Keycloak, Caddy), owner login (Keycloak, hi/en), caretaker link login, roles, farm access check, settings, outbox, adapters + fakes, CI + staging workflow files | Deploy to a staging host (no host chosen); CI never run on GitHub |
| M1 | Crop library | Built, data empty | 65 crops, 10 recipe shells, 12 engine rules (draft); review workflow; agronomist screens (crops, recipes, review queue) | Agronomy values (every field `TODO(agronomist)`); an agronomist to approve 40 crops + 6 recipes; pests (no screen, no seed); companions/rules/varieties screens; crop-to-mandi-commodity mapping |
| M2 | Parcel + site intelligence | Built, mostly | Setup wizard (4 steps, hi/en), draw/type/four-sides plot, place search, farm page, site profile (climate, terrain, soil, region, road distance, nearby places), confirm/change flow | Mandi prices (needs data.gov.in key); groundwater class (no cited data); gate + obstacle marking; 1 m map grid; KML upload; schemes table; curated places (KVK, FPO); the 10-location acceptance run |
| M3 | Design engine | Not started | Rules seeded as drafts | Everything: templates, zone carving, bed tiling, crop assignment, estimates, plan view, plan editor |
| M4 | Planner, tasks, shopping list | Not started | - | Plantings, task generation, This week screen, missed-sowing and failure rules, shopping list |
| M5 | Telegram messaging | Not started | `Channel` interface + fake, caretaker link login | Bot, invite acceptance, daily/weekly sends, reply flows, text parser |
| M6 | Records and money | Not started | - | Logs (online + offline), profit, plan vs actual |
| M7 | AI helper + legal | Not started | LLM/embedding interfaces + fakes, `library.approved` event | RAG, tools, guardrails, evals; terms, privacy, disclaimer, export, delete |
| M8 | Beta | Not started | - | Own plot + 5-10 users, metrics |

## MVP features (spec section 1)

| Feature | State |
|---|---|
| Plan: location, land, site facts | Done (engine that produces the plan: not started) |
| Tasks to the caretaker on Telegram | Not started |
| Logs | Not started |
| Money / profit | Not started |
| AI helper | Not started |
| Shopping list | Not started |
| Legal basics | Not started |

## Blockers and decisions needed

1. **GitHub**: this machine has no credentials, so `main` and the branches `m0-foundation` -> `m1-crop-library` -> `m2-parcel-site` are local only.
2. **Agronomy data**: no values exist yet. M3 cannot choose crops without them. Needs an agronomist, or small cited-research batches.
3. **Staging host** (Oracle free VM / own machine + tunnel / small VPS) and a real `.env`.
4. **Keys**: `DATA_GOV_IN_API_KEY` (mandi prices), a real `GEOCODER_USER_AGENT` contact; later a Telegram bot token (M5) and an LLM choice (M7).
5. **Satellite tiles**: off until a licensed provider is chosen.

## Known gaps and debts (not blocking)

- Lean mode: tests, CI runs, security scans, evals and monitoring are deferred by decision. Only a few backend tests exist.
- Deferred review items from M0 (see `docs/decisions.md`): pin GitHub Actions by SHA, per-key validation of admin settings, split compose networks + Valkey password, JWKS refresh throttling, caretaker logout, stronger module-boundary contracts, paginated list envelopes.
- SoilGrids is rate-limited (~5 calls/min) and sometimes slow; soil may be missing on a cold lookup.
- Hindi strings need a native-speaker review.
- Keycloak imports the realm only on first start; later realm-file changes need the admin console.
- Local Docker needs a few GB of free memory to prepare the OSRM road map.
