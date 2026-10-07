# Project status

Last updated: 2026-10-07 (research batch 6; see `docs/vision.md` for scope). Source of truth for scope: `docs/spec/` (milestones in `15-build-order-and-open-questions.md`).
Everything below runs on the local Docker stack. Nothing is pushed to GitHub yet (see "Blockers").

## Milestones

| # | Milestone | State | What exists | What is missing |
|---|---|---|---|---|
| M0 | Foundation | Built, local | Compose stack (Postgres+PostGIS+pgvector, Valkey, SeaweedFS, Keycloak, Caddy), owner login (Keycloak, hi/en), caretaker link login, roles, farm access check, settings, outbox, adapters + fakes, CI + staging workflow files | Deploy to a staging host (no host chosen); CI never run on GitHub |
| M1 | Crop library | Built: 71 crops AI-checked, 77 crop pairs, 10 recipes, 54 pests and diseases, FAO water coefficients for 34 crops (all AI-checked, none expert-approved) | 65 crops, 10 recipe shells, 12 engine rules (draft); review workflow; agronomist screens (crops, recipes, review queue); `ai_verified` status + beta flag; research batches 1-3 (9 crops AI-checked: tomato, brinjal, okra, bottle gourd, cucumber, radish, peas, methi, coriander; chilli, onion and palak drafts) | Agronomy values for the other crops; an agronomist to approve 40 crops + 6 recipes; pests (no screen, no seed); rules/varieties screens; crop-to-mandi-commodity mapping |
| M2 | Parcel + site intelligence | Built, mostly (schemes table and 12 cited schemes added 2026-10-06) | 2-screen onboarding (GPS, coordinates, size only), interactive plot editing (drag corners/shape, corner points), Google satellite (needs key), farm page with insights + Improve card, place search, farm page, site profile (climate, terrain, soil, region, road distance, nearby places), confirm/change flow | Mandi prices (needs data.gov.in key); groundwater class (no cited data); gate + obstacle marking; 1 m map grid; KML upload; schemes table; curated places (KVK, FPO); the 10-location acceptance run |
| M3 | Design engine | In progress (engine 0.3.1) | Layout (zones + beds), crops per bed/layer/season, trees in the orchard strip, curry-leaf hedge, flowers when chosen, polyhouse and livestock zones when chosen, five goal-driven options with comparison, owner editing (land use, bed size, swap, use this plan), goal step in setup, visuals (map, bed side view with machan/polyhouse, year strip, How this plan farms), schemes matched to the plan | Water check, cost and income estimates, intercrops between young trees, animal numbers, polyhouse crop calendars, more crops (vegetables, soil builders, mango and amla gaps), golden/property tests |
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
5. **Satellite tiles**: off until a licensed provider is chosen (Google Map Tiles planned; needs a key). Comparing Google, Mapbox and MapTiler on the real plots is pending.
6. **Open vision questions** (see `docs/vision.md`): the cut-off sixth pillar, and the home-screen pitch.

## Direction (decided 2026-10-05)
- Scope: 1 bigha and up; owner + caretaker or owner-farmer; first beta on the owner's own land.
- New pillars: goal-driven competing plans, government schemes and benefits (cited, "may be eligible").
- Schemes and benefits: built (12 cited schemes, matched to the plan, card on the farm page).
- Next slices: cost and income estimates with the subsidy beside setup cost, the water check, then the This week card (M4); research batch 5 (more vegetables, soil builders, mango and amla gaps, border plants), jeevamrut and pest-spray recipes.

## Known gaps and debts (not blocking)

- Lean mode: tests, CI runs, security scans, evals and monitoring are deferred by decision. Only a few backend tests exist.
- Deferred review items from M0 (see `docs/decisions.md`): pin GitHub Actions by SHA, per-key validation of admin settings, split compose networks + Valkey password, JWKS refresh throttling, caretaker logout, stronger module-boundary contracts, paginated list envelopes.
- SoilGrids is rate-limited (~5 calls/min) and sometimes slow; soil may be missing on a cold lookup.
- Hindi strings need a native-speaker review.
- Keycloak imports the realm only on first start; later realm-file changes need the admin console.
- Local Docker needs a few GB of free memory to prepare the OSRM road map.
