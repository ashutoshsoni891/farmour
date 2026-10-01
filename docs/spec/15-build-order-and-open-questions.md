## 15. Build order and open questions

Build in this order; each milestone ends with its definition of done met and deployed to staging. Durations assume about 10–12 hours a week.

| # | Milestone | Scope | Definition of done | Est. weeks |
| --- | --- | --- | --- | --- |
| M0 | Foundation | Repo, Docker Compose (Postgres + PostGIS + pgvector, Valkey, SeaweedFS, Keycloak, Caddy), auth (Keycloak + caretaker link login), module scaffold, outbox events, adapter interfaces, import-linter contracts, roles, settings, i18n, CI | Login in `en`/`hi`, role checks tested, deploy from main to staging | 2 |
| M1 | Crop library | Schema, admin UI, seed 60 crops + 10 recipes + pests, regions, review workflow | Agronomist has approved at least 40 crops and 6 recipes | 3 (overlaps M2) |
| M2 | Parcel + site intelligence | Setup wizard, map drawing, measurements entry, site data adapters (climate, soil, elevation, land cover, groundwater table, mandi price ingest, routing, places), "We found" card | Section 17 acceptance passes for 10 test locations | 3 |
| M3 | Design engine | Templates, zone carving, bed tiling, crop assignment using the site profile, estimates, plan view | Golden and property tests pass; agronomist signs off 9/10 plans | 4 |
| M4 | Planner, tasks, shopping list | Plantings, task generation, This week screen, missed-sowing and failure rules, shopping list | 12-month plan generates tasks with no duplicates; shopping list quantities match plan | 2 |
| M5 | Telegram messaging | Bot, invite and linking, daily and weekly sends, reply flows, text parser | A test caretaker completes a week via Telegram only | 2 |
| M6 | Records and money | Logs (online and offline), profit, plan vs actual | Figures match a hand-calculated test farm | 1–2 |
| M7 | AI helper + legal basics | Text Q&A with RAG and tools, guardrails, evals; terms, privacy, estimates disclaimer, data export and delete | Eval set ≥ 90% factual, 0 unsafe; legal pages live; export and delete work | 2 |
| M8 | Beta | Own 800 sq ft plot + 5–10 users, feedback loop, fixes | MVP metrics tracked for 4 weeks | ongoing |

Total: about **13–15 weeks of evenings** to the beta, with M1 overlapping M2.

### Beta success metrics

Users following the plan past week 4 ≥ 70%; weekly tasks done ≥ 60%; users logging harvests regularly ≥ 50%; at least 3 of 10 users willing to pay Rs 299–999 a month.

### Open questions to settle before or during the build

- [ ] Who is the agronomist, and how many hours a week? (Needed from M1.)
- [ ] Final values for engine defaults: bed width, path width, crowding factors, cost per sqm by zone kind.
- [ ] Satellite tile provider and its licence terms for a commercial app.
- [ ] WhatsApp Business account verification and template approval timeline.
- [ ] Hosting: Oracle Cloud free VM, own machine + Cloudflare Tunnel, or a small paid VPS once beta users depend on it.
- [ ] Local bigha size to offer as presets for Indore-area districts (user-entered in v1).
- [ ] Pricing plans and whether the beta is free.
- [ ] Whether caretakers get the PWA at all in v1, or WhatsApp only.

