## 16. Extensibility, scaling and change rules

These rules are binding for every module: new features, regions, channels and providers must be added by plugging in, not by rewriting existing code.

### Architecture principles

- **Modular monolith with ports and adapters.** Each module (`parcel`, `layout`, `library`, `planner`, `records`, `weather`, `messaging`, `ai`, `export`) has the same internal shape: `api.py` (routes), `service.py` (the only public entry point), `schemas.py` (Pydantic contracts), `repository.py` (database access), `events.py`, `tests/`.
- **No module touches another module's tables.** Cross-module calls go through the other module's `service.py` or through domain events. Enforce this in CI with `import-linter` contracts; a violation fails the build.
- **Outside services only through adapters** (`app/adapters/`): LLM, embeddings, object storage, messaging channels, weather, geocoding, map tiles, email. Each adapter has an interface, one or more implementations, and a fake for tests. The active implementation is chosen by config.
- **Stateless processes, config from environment** (12-factor). Any API or worker container can be restarted or duplicated at any time.
- **Rules and agronomy are data, not code.** Crops, sow windows, spacing, zone templates, scoring weights, alert thresholds and message texts live in database tables or seed files, so an agronomist or admin can change them without a deploy.

### Domain events (how new features plug in)

Modules publish events to an `outbox` table in the same transaction as the change; a Celery worker delivers them to subscribers, with retries and idempotency keys. Events carry IDs and a version, never whole objects.

| Event | Published when | MVP subscribers | Future subscribers |
| --- | --- | --- | --- |
| `plan.activated` | Owner activates a plan | Planner (create tasks) | Analytics, FPO dashboard |
| `task.completed` | Task marked done | Records (streaks, stats) | Gamification, reminders |
| `log.created` | Harvest, cost, sale or photo logged | Profit, photo check | Marketplace (sellable produce), FPO reports |
| `planting.failed` | Crop failure reported | Planner (replacement offer) | Agronomist alerts, insurance data |
| `alert.raised` | Weather rule crossed | Planner, messaging | IoT automation (e.g. start irrigation) |
| `library.approved` | Library entry approved | AI (re-embed), layout (cache clear) | Plan-update suggestions |

### Registries (extension points)

Each extension point is a registry keyed by a string, filled at startup; adding a new one means adding a class and registering it, with no edits to existing code.

| Registry | MVP entries | Add later without touching core code |
| --- | --- | --- |
| Zone templates | T, S, M, L | Polyhouse, orchard-only, FPO block layouts |
| Placement and scoring strategies | Default greedy scorer | Solver-based (OR-Tools), income-max, water-min |
| Task generators | Section 8 task types | Livestock, IoT maintenance, harvest-to-sale |
| Alert rules | Heat, rain, wind, cold, dry spell | Pest-risk models, sensor-based rules |
| Messaging channels | Telegram | WhatsApp, SMS, voice call |
| LLM / embedding providers | Via LiteLLM | Any hosted or local model |
| Export formats | PDF, share link | Excel, KML, print posters |
| Languages | `en`, `hi` | Marathi, Gujarati and others (i18n files + library translations) |

### Schema choices made now so growth needs no migration pain

- Add a `regions` table (e.g. `malwa`) and a `region_id` on crops' sow windows, prices, rules and templates. Launching in a new state becomes a new dataset, not new code.
- Add a nullable `organization_id` on `farms` and an `organizations` table (unused in the MVP) so FPO and NGO accounts can group farms later.
- Use UUID keys everywhere, `jsonb` `metadata` columns on farms, plans and logs for experimental fields, and soft deletes.
- Reserve `devices` and `readings` table names for IoT; do not create them until needed.

### Changing things safely

- **API:** versioned under `/api/v1`; only additive changes within a version; breaking changes go to `/api/v2` with at least 3 months of overlap. The TypeScript client is generated from OpenAPI, and CI fails if the contract changes without a version note.
- **Database:** Alembic migrations using expand → migrate data → contract across separate releases; never drop or rename a column in the same release that stops using it.
- **Feature flags:** new behaviour ships behind a flag in `settings` (per environment, optionally per farm) so it can be turned on for your own plot first.
- **Engine and prompts:** every change bumps `engine_version` or the prompt version; golden layout tests and AI evals must pass; active plans keep their old version until the owner accepts an update.
- **Decisions:** any structural choice gets a short record in `docs/decisions.md` (context, decision, consequences).

### Code quality gates

- Typed code (mypy strict for backend modules, TypeScript strict); ruff formatting.
- Test coverage: design engine and profit calculations ≥ 90%, overall ≥ 75%.
- Each module has a README: purpose, public service functions, events published and consumed, settings used.
- A `make new-module NAME=x` scaffold creates the standard module shape so every module looks the same.

### Scaling steps by stage

| Stage (approx.) | What changes | What stays the same |
| --- | --- | --- |
| Beta: up to 100 farms | One server, Docker Compose | — |
| Up to 5,000 farms | Separate database server; 2–3 API containers; dedicated Celery queues (`messaging`, `ai`, `default`); Valkey caching of plans and library | Code, images, schema |
| Up to 50,000 farms | Managed Postgres with read replica; object storage cluster or hosted S3; Kubernetes (k3s) with autoscaling workers; CDN for the PWA and map assets | Code, images, schema |
| Beyond | Split a hot module (e.g. messaging or AI) into its own service; it already talks through events and a service interface, so the split is mechanical | Other modules unchanged |

### Definition of done for any change

- [ ] Stays inside its module boundary (import-linter passes)
- [ ] New outside dependency added only as an adapter, passing the selection rules in section 4
- [ ] Tests added; golden tests and AI evals pass where relevant
- [ ] Migration follows expand → contract; API change is additive or versioned
- [ ] Behind a feature flag if user-facing and risky
- [ ] Module README and `docs/decisions.md` updated when behaviour or structure changes

