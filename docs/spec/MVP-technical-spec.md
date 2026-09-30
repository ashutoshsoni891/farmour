# MVP technical spec — farm planning platform

Sep 28, 2026 · @Aashutosh

This tab is the build spec for the MVP. It is written so a coding agent can implement the platform from it without other context; the main tab covers the business case.

## 1. Purpose, scope and non-goals

The MVP turns a real piece of land (terrace to about 2 acres) into a zoned, multilayer organic farm plan, tells the person doing the work what to do each week, and tracks whether it earns.

### Problem statement

"I have land, but I don't know what to grow where and when, my caretaker or family doesn't know what to do each day, and I can't tell whether it's making money."

### MVP scope (lean) — build only these

1. **Plan:** the owner pins the location and draws the land; site intelligence auto-fills soil, climate, water stress, local prices and distances (section 17); the owner confirms; the design engine returns zones, beds and crops per layer (section 7).
2. **Tasks:** a weekly and daily task list per bed, sent to the caretaker in Hindi on Telegram, with done / not-done replies (sections 8 and 10).
3. **Logs:** harvest, cost, sale and photo (photos are stored, not analysed) (section 9).
4. **Money:** profit per zone and plan versus actual (section 9).
5. **AI helper:** text questions and answers grounded in the crop library, the farm's data and its site profile (section 11).
6. **Shopping list:** seeds, saplings and inputs to buy each season, with quantities, rough cost and nearest source (section 8).
7. **Legal basics:** terms, privacy notice, an "all figures are estimates" disclaimer, data export and account deletion (section 14).

### Post-MVP (designed, but do not build now)

- Forecast-based weather alerts and weather rescheduling (section 9)
- Photo diagnosis (section 11) and plan PDF / share link export
- WhatsApp channel (Telegram only in the MVP), voice notes to text, read-aloud tasks
- Selling helper, proof-of-work photos, how-to guides, end-of-season report, admin support tools beyond basic user management
- IoT and sensors, FPO dashboards, marketplace and payments, satellite crop monitoring, native mobile apps, livestock planning

Where a later section describes a post-MVP feature it is marked "post-MVP"; keep the interfaces and table names reserved so it plugs in later, but do not implement it.

### How a coding agent should use this spec

- Build in the order of section 15; each milestone has a definition of done.
- Where this spec gives a number (spacing, threshold, limit), treat it as a **config value** in the `settings` table or crop library, never a hard-coded constant.
- Where the spec is silent, choose the simplest option and record it in `docs/decisions.md`.
- Agronomy facts come only from the crop library (section 6). Code and prompts must never invent spacing, seasons or remedies.
- All user-facing strings go through i18n keys (`en`, `hi`) from the first commit.
- Units: metres and square metres internally; display sq ft, acres and bigha by user preference. Money in integer paise; display INR.
- Time zone: store UTC, display and schedule in `Asia/Kolkata`.

Section 16 (extensibility, scaling and change rules) applies to every module and every milestone; treat it as binding, not optional.

## 2. Users, roles and permissions

Four roles; permissions are per farm, so one person can be owner of one farm and caretaker on another.

| Role | Uses | Can do | Cannot do |
| --- | --- | --- | --- |
| Owner | Web app (PWA) | Create farms, draw parcels, generate and edit plans, invite caretakers, see all logs and money, export plans | Edit the global crop library |
| Caretaker | WhatsApp first; PWA optional | Receive tasks, mark done / skip, log harvest, cost and photos, ask the AI helper | See sale prices or profit (unless owner enables `caretaker_sees_money`), edit plans, delete logs |
| Agronomist | Web admin | Create and edit crop library entries, rules and recipes; review and approve; flag unsafe AI answers | Access individual farms unless an owner shares one for review |
| Admin | Web admin | Manage users, settings, feature flags, message templates; view audit log | — |

**Rules:**

- Auth (no SMS cost): owners, agronomists and admins log in through Keycloak (email + password, Google, or passkey). Caretakers never need a password: the owner's invite sends a one-time link that binds their Telegram (later WhatsApp) account to the farm; for the PWA they get a single-use login link in the chat. Phone number is stored as contact identity; paid SMS OTP can be added later.
- A caretaker is invited by phone number; the invite is accepted by replying on WhatsApp or opening a link. No password needed.
- Membership table `farm_members(farm_id, user_id, role)` decides access; every API call checks it.
- Every write records `created_by`, and changes to plans, library entries and money logs go to `audit_log`.

## 3. System architecture

The MVP is a modular monolith: one FastAPI backend with clear internal modules, one Postgres database, S3-compatible object storage for files, and four external services, all self-hosted with Docker Compose. Split modules into separate services only when load demands it.

&#91;embedded content: Lean MVP architecture · 9 modules incl. site intelligence · open-source, self-hosted · no IoT\]

### Module responsibilities

| Module | Owns | Reads from | Never does |
| --- | --- | --- | --- |
| Parcel and layout | `parcels`, `zones`, `beds`, `bed_layers` | Crop library, settings | Call the LLM to decide geometry |
| Crop library | `crops`, `crop_varieties`, `companions`, `recipes`, `pests`, `rules` | — | Publish entries not approved by an agronomist |
| Planner and tasks | `plans`, `plantings`, `tasks` | Layout, library, weather | Delete completed tasks |
| Records and profit | `logs`, `sales`, `costs`, profit views | Plantings, tasks | Show money to caretakers without permission |
| AI helper | `ai_conversations`, `ai_messages`, `photo_checks` | Library (pgvector), farm data (read-only tools) | Write to plans or library |
| Weather alerts | `weather_snapshots`, `alerts` | Open-Meteo | Send more than 1 alert per farm per day unless severe |
| Messaging | `messages`, `message_templates`, `wa_sessions` | Tasks, alerts | Send free-form WhatsApp outside the 24-hour window |
| Plan export | `exports` | Layout, plan | Expose private farms without a signed link |
| Scheduler | `jobs` | All modules | Run a job twice for the same key (idempotency) |

**MVP module changes:** add **Site intelligence** (owns `site_facts`, `mandis`, `mandi_prices`, `places`, `schemes`, `geo_cache`; section 17). The shopping list is part of the planner module. Weather alerts, photo check and plan export are post-MVP; their rows above describe the future design.

### Walkthrough: from drawing a plot to a caretaker's WhatsApp

1. Owner draws the parcel on the map; the API stores it as a PostGIS polygon and computes area and orientation.
2. Owner picks goal, budget and start date; the layout module generates zones, beds and layers using library rules (section 7).
3. Owner accepts the plan; the planner creates plantings and a dated task list (section 8).
4. Every Sunday 18:00 IST the scheduler sends each caretaker their week's tasks on WhatsApp; each day at 07:00 IST it sends that day's tasks.
5. Caretaker replies "done" / "not done" or sends a photo or harvest amount; messaging parses it and writes a log.
6. Weather job runs at 05:30 IST; if a threshold is crossed it shifts affected tasks and alerts owner and caretaker.
7. Owner sees plan-vs-actual and profit on the dashboard.

## 4. Tech stack, hosting, repo layout and configuration

The MVP runs on open-source software, self-hosted with Docker Compose on one free or low-cost server, for close to zero monthly cost. Every third-party dependency sits behind an interface (LLM, storage, messaging, weather), so moving to AWS or another cloud later is a configuration change, not a rewrite.

### Stack

| Layer | Open-source choice | Notes |
| --- | --- | --- |
| Backend | Python 3.12, FastAPI, Pydantic v2, SQLAlchemy 2 + Alembic | OpenAPI generated and used for the frontend client |
| Geometry | Shapely 2, pyproj | Compute in UTM 43N (EPSG:32643) for Indore; store WGS84 (EPSG:4326) |
| Database | PostgreSQL 16 + PostGIS 3 + pgvector, in Docker | One database for everything, including jobs and vectors |
| Jobs and scheduler | Celery workers + Celery beat (schedules), with Valkey as broker and cache | Most widely used Python task queue; scale by adding workers. Valkey is the Linux Foundation's BSD-licensed, Redis-compatible fork; also used for rate limits |
| Object storage | SeaweedFS (Apache 2.0, S3-compatible, scales from one node to a cluster) | Do not use MinIO: its open-source edition was archived in 2026 and gets no security patches. Code uses the S3 API (boto3), so it can point to Cloudflare R2, Backblaze B2 or AWS S3 later |
| Auth | Keycloak (OpenID Connect) for owners, agronomists and admins: email + password, Google login, passkeys; FastAPI only validates Keycloak's tokens. Caretakers are identified by their messaging-app account, linked through a one-time invite link | Keycloak is the most widely used open-source identity server; never write password or token handling by hand. It has no built-in email magic link, so none is used. No SMS cost |
| AI orchestration | LangGraph + LiteLLM (one interface to any LLM provider) | Switch providers by config |
| LLM | Development: a local open model via Ollama. Beta: a hosted model on a free tier or small pay-as-you-go budget | Pick by the Hindi eval set (section 14); check current free-tier limits |
| Embeddings | BGE-M3 (multilingual, 1024 dimensions, Hindi supported) via sentence-transformers on CPU | Free; runs on the server |
| Messaging | Telegram Bot API for the beta (free); WhatsApp Cloud API later | Behind a `Channel` interface; same flows on both (section 10) |
| Weather | Open-Meteo API | Its free API is for non-commercial use; for a paid product, buy their plan or self-host Open-Meteo (open source) |
| Maps | MapLibre GL + Terra Draw; OpenStreetMap-based vector tiles (e.g. OpenFreeMap) | Free satellite imagery for commercial use is limited: check each provider's licence; the "enter measurements" path must always work |
| Geocoding | Nominatim (respect its usage policy) or self-hosted Photon | Village search in the setup wizard |
| PDF | WeasyPrint | Bed map rendered as SVG then PDF |
| Frontend | React 18 + TypeScript + Vite, TanStack Query, Tailwind; PWA via Workbox; IndexedDB (Dexie) for offline | Same as before |
| i18n | i18next (`en`, `hi`) | Hindi first-class |
| Web server | Caddy (automatic HTTPS via Let's Encrypt) | Reverse proxy for API, frontend and storage |
| CI / images | GitHub Actions, GitHub Container Registry | Free for small projects |
| Errors and uptime | GlitchTip (Sentry-compatible), Uptime Kuma | Self-hosted; GlitchTip uses the standard Sentry SDK, so moving to Sentry later is a DSN change |
| Product analytics | Umami (self-hosted) or events in Postgres | For the MVP metrics |
| Backups | Nightly `pg_dump` + restic to a free-tier bucket (e.g. Backblaze B2 or Cloudflare R2) | Encrypted; 14-day retention |

### Hosting options (pick one)

| Option | Monthly cost (approx.) | Trade-off |
| --- | --- | --- |
| Oracle Cloud Always Free ARM VM | Rs 0 | Generous free resources; sign-up and capacity availability can be unpredictable |
| Your own machine + Cloudflare Tunnel | Rs 0 (plus electricity) | Good for development and a tiny beta; down whenever the machine is off |
| Small VPS (e.g. Hetzner or similar) | about Rs 400–800 | Reliable and simple; recommended once real users depend on it |
| Supabase free tier for Postgres (+ PostGIS, pgvector) | Rs 0 | Managed database with limits; free projects pause when idle |

**Expected running cost in the beta:** server Rs 0–800, domain about Rs 70 a month, LLM Rs 0–1,000 depending on usage and provider, messaging Rs 0 on Telegram. Total roughly **Rs 0–2,000 a month**. All figures are estimates; check current pricing.

### Selection rules for any open-source component

Every dependency must be: widely used with an active maintainer community (recent releases, security advisories handled), under a permissive or well-understood licence (MIT, BSD, Apache 2.0, PostgreSQL; AGPL only for separate services you run unmodified), well documented, available as an official Docker image, and replaceable behind an adapter. Record any exception in `docs/decisions.md`.

### Security hygiene (from the first commit)

- Pin every Docker image and package version; Renovate or Dependabot opens update PRs weekly.
- CI runs: ruff + mypy, bandit (Python security lint), pip-audit, npm audit, Trivy image and filesystem scan, secret scanning (gitleaks). A high-severity finding blocks the merge.
- Only Caddy is exposed (ports 80/443); Postgres, Valkey, SeaweedFS and the Keycloak admin console listen on the internal Docker network only; SSH is key-only.
- Server: automatic OS security updates, firewall (ufw), CrowdSec or fail2ban for brute-force protection.
- Containers run as non-root with read-only file systems where possible; resource limits set in Compose.
- Keycloak: brute-force detection on, strong password policy, admin account with passkey or 2FA.

### Scaling path (no rewrite needed)

| When | Step |
| --- | --- |
| More API traffic | Run more `api` containers behind Caddy; the API is stateless |
| More background jobs or AI calls | Add Celery workers; separate queues for `messaging`, `ai`, `default` |
| Database load | Move Postgres to its own server or a managed Postgres; add a read replica for dashboards |
| Files grow | Point the S3 adapter at a larger SeaweedFS cluster or a hosted S3-compatible store |
| Many servers | Move from Docker Compose to Kubernetes (k3s) using the same images |

### Repo layout (monorepo)

```
farm-platform/
  backend/
    app/
      api/            # routers per module
      core/           # config, auth, permissions, i18n, errors
      adapters/       # interfaces + implementations: llm, storage, channel (telegram, whatsapp), weather, geocode
      modules/
        parcel/  layout/  library/  planner/  records/
        weather/  messaging/  ai/  export/
      jobs/           # Celery tasks + beat schedule, idempotent
      db/             # models, Alembic migrations
    seeds/            # crop library CSV/JSON, rules, message templates
    tests/            # unit, integration, golden layouts
  frontend/
    src/ (pages, components, map, offline, i18n/en.json, i18n/hi.json)
  deploy/
    docker-compose.yml   # api, worker, beat, postgres, valkey, seaweedfs, keycloak, caddy, glitchtip, uptime-kuma
    Caddyfile
    backup/              # pg_dump + restic scripts, cron
  docs/ (decisions.md, api.md, runbook.md)
```

### Environments and configuration

- Environments: `local` (Docker Compose on your laptop), `staging` and `prod` (same Compose file, different `.env`). Staging uses a separate Telegram bot.
- Secrets in `.env` files outside the repo with restricted file permissions (or Docker secrets): `DATABASE_URL`, `VALKEY_URL`, `KEYCLOAK_URL`, `KEYCLOAK_REALM`, `KEYCLOAK_CLIENT_ID`, `LINK_SIGNING_SECRET`, `LLM_PROVIDER`, `LLM_MODEL`, `LLM_API_KEY`, `EMBEDDING_MODEL`, `S3_ENDPOINT`, `S3_ACCESS_KEY`, `S3_SECRET_KEY`, `S3_BUCKET`, `SMTP_HOST`, `SMTP_USER`, `SMTP_PASSWORD` (Keycloak emails), `TELEGRAM_BOT_TOKEN`, `TELEGRAM_WEBHOOK_SECRET`, `WA_TOKEN` / `WA_APP_SECRET` / `WA_PHONE_NUMBER_ID` (later), `GLITCHTIP_DSN`.
- Tunable values live in a `settings` table (key, value JSON, updated\_by), cached 5 minutes. Examples: `bed_width_m`, `path_width_m`, `weekly_digest_time`, `heat_alert_c`, `max_ai_messages_per_day`.
- Portability rule: no module imports a provider SDK directly; everything goes through `app/adapters/`.

## 5. Data model

All tables have `id uuid pk`, `created_at`, `updated_at` (timestamptz, UTC) and, where users write, `created_by uuid`. Soft delete via `deleted_at` on user content; hard delete only by admin. Geometry is `geometry(Polygon, 4326)` unless noted.

```sql
-- Identity
users(id, phone text unique not null, name text, email text null,
      language text check (language in ('en','hi')) default 'hi',
      unit_pref text check (unit_pref in ('sqft','acre','bigha','sqm')) default 'sqft',
      bigha_sqft numeric null,            -- local bigha size, user-set; no default
      is_admin bool default false, is_agronomist bool default false)
farm_members(farm_id, user_id, role text check (role in ('owner','caretaker')),
             caretaker_sees_money bool default false, primary key(farm_id, user_id))
invites(id, farm_id, phone, role, token, expires_at, accepted_at)

-- Farm and land
farms(id, name, site_type text check (site_type in ('ground','terrace')),
      district text, village text, lat numeric, lng numeric,
      goal text check (goal in ('home_food','income','both')),
      budget_setup_paise bigint, budget_monthly_paise bigint,
      labour text check (labour in ('self','family','caretaker','mixed')),
      water_source text check (water_source in ('bore','well','canal','municipal','rain_only')),
      water_summer_lpd int null,          -- litres/day available in May
      electricity bool, livestock bool default false)
parcels(id, farm_id unique, boundary geometry(Polygon,4326) not null,
        area_sqm numeric not null, perimeter_m numeric,
        north_bearing_deg numeric default 0, -- rotation of drawn plot vs true north
        soil_type text check (soil_type in ('black','red','sandy','clay','loam','mixed','unknown')),
        soil_depth_cm int null, drainage text check (drainage in ('good','ok','waterlogs')),
        slope_dir text null,                -- 'N','NE',... or null for flat
        terrace_load_kg_per_sqm numeric null,-- required when site_type = terrace
        obstacles jsonb default '[]')       -- trees, tank, stairs as GeoJSON features

-- Plan and layout
plans(id, farm_id, version int, status text check (status in ('draft','active','archived')),
      start_date date, engine_version text, inputs jsonb, -- snapshot of inputs used
      summary jsonb,                       -- areas, costs, expected income
      unique(farm_id, version))
zones(id, plan_id, kind text check (kind in ('beds','orchard','rotation','border','water','utility','nursery','path','livestock')),
      geom geometry(Polygon,4326), area_sqm numeric, label text)
beds(id, zone_id, code text,              -- 'B1','B2' shown to users
     geom geometry(Polygon,4326), length_m numeric, width_m numeric,
     raised bool, orientation_deg numeric, has_trellis bool)
bed_layers(id, bed_id, layer text check (layer in ('underground','surface','middle','climber','canopy')),
           season text check (season in ('kharif','rabi','zaid','perennial')),
           crop_id, variety_id null, plant_count int, spacing_cm int)
plantings(id, plan_id, bed_id, layer, crop_id, variety_id null,
          planned_sow date, actual_sow date null, planned_harvest_start date,
          planned_harvest_end date, status text check (status in
          ('planned','sown','growing','harvesting','done','failed','skipped')),
          expected_yield_kg numeric, failure_reason text null)

-- Tasks
tasks(id, farm_id, planting_id null, bed_id null,
      type text,                           -- see section 8
      title_key text, params jsonb,        -- i18n key + values, never raw text
      due_date date, window_days int default 2,
      status text check (status in ('pending','sent','done','skipped','overdue','cancelled')),
      assignee_id null, done_at null, done_via text check (done_via in ('whatsapp','web')) null,
      source text check (source in ('plan','weather','manual','recipe')),
      idempotency_key text unique)

-- Records
logs(id, farm_id, bed_id null, planting_id null,
     kind text check (kind in ('harvest','cost','sale','photo','note','issue','water')),
     qty numeric null, unit text null,     -- kg, bunch, piece, litre
     amount_paise bigint null, category text null, -- cost: seed, input, labour, water, transport, tools, other
     photo_s3_key text null, note text null, occurred_on date,
     source text check (source in ('whatsapp','web','offline_sync')),
     client_uuid uuid unique null)         -- dedupe offline retries

-- Library (section 6), AI, messaging, weather, system
crops, crop_varieties, companions, recipes, pests, rules, library_chunks (embedding vector(1024))
ai_conversations(id, farm_id, user_id, channel), ai_messages(id, conversation_id, role, content, citations jsonb, tokens_in, tokens_out)
photo_checks(id, farm_id, log_id, result jsonb, confidence numeric, reviewed_by null)
messages(id, farm_id, user_id, direction, wa_message_id unique, template_name null, body jsonb, status, error null)
wa_sessions(user_id, last_inbound_at, state jsonb)   -- 24h window + conversation state
weather_snapshots(id, cell_key, fetched_at, forecast jsonb)
alerts(id, farm_id, kind, severity, starts_on, payload jsonb, sent_at null)
exports(id, plan_id, s3_key, share_token unique, expires_at)
jobs(id, name, run_key unique, status, attempts, last_error, run_at)
settings(key pk, value jsonb, updated_by)
audit_log(id, actor_id, entity, entity_id, action, before jsonb, after jsonb)
```

**Indexes:** GiST on all geometry columns; `tasks(farm_id, due_date, status)`; `logs(farm_id, occurred_on)`; `plantings(plan_id, status)`; HNSW on `library_chunks.embedding`; unique `messages.wa_message_id` for webhook dedupe.

**Invariants the code must enforce:**

- Every bed geometry lies inside its zone; every zone inside the parcel; zones do not overlap (check with `ST_Within` / `ST_Overlaps` after generation).
- One `active` plan per farm. Editing an active plan creates a new version; old tasks for removed plantings become `cancelled`, never deleted.
- `terrace_load_kg_per_sqm` is required before generating a terrace plan (section 7).

**Also create from M0** (section 16): `regions(id, slug, name_en, name_hi)` with `region_id` on sow windows, prices, rules and templates; `organizations(id, name, kind)` with nullable `farms.organization_id`; `outbox(id, event, version, payload jsonb, created_at, delivered_at, attempts)`; and a `metadata jsonb` column on farms, plans and logs.

## 6. Crop library

The library is the product's source of truth: the design engine, planner and AI helper read only from it. Nothing reaches users until an agronomist approves it.

### Schema

```sql
crops(id, slug unique, name_en, name_hi, family text,        -- 'cucurbit','solanaceae',...
      category text check (category in ('vegetable','leafy','root','spice','fruit_tree','fruit_short','pulse','cereal','millet','herb','border','green_manure','flower')),
      layers text[],                    -- allowed: underground/surface/middle/climber/canopy
      seasons text[],                   -- kharif/rabi/zaid/perennial
      sow_windows jsonb,                -- [{"from":"10-01","to":"11-15","method":"direct|transplant"}] Malwa
      nursery_days int null,            -- days in nursery before transplant
      days_to_first_harvest int, harvest_span_days int,
      spacing_row_cm int, spacing_plant_cm int, rows_per_1_2m_bed int,
      height_max_cm int, root_depth_cm int,
      sun text check (sun in ('full','partial','shade_tolerant')),
      water_need text check (water_need in ('low','medium','high')),
      water_l_per_sqm_day jsonb,        -- by growth stage
      heat_tolerance_c int, cold_tolerance_c int,
      waterlogging_tolerant bool, terrace_ok bool, min_container_depth_cm int null,
      expected_yield_kg_per_sqm numeric, yield_unit text default 'kg',
      price_mandi_paise_per_kg bigint, price_direct_paise_per_kg bigint, price_updated_on date,
      years_to_bear numeric null, lifespan_years int null,   -- perennials
      tree_spacing_m numeric null, canopy_diameter_m numeric null,
      status text check (status in ('draft','in_review','approved','retired')),
      approved_by null, approved_at null, source_notes text)
crop_varieties(id, crop_id, name, days_to_first_harvest, notes, status)
companions(crop_a, crop_b, relation text check (relation in ('good','avoid')), reason_en, reason_hi)
pests(id, crop_ids uuid[], name_en, name_hi, symptoms_en, symptoms_hi, months int[], recipe_ids uuid[], escalate_if text)
recipes(id, slug, name_en, name_hi,           -- jeevamrut, beejamrut, neemastra, dashparni ark, vermicompost...
        ingredients jsonb, per_area_sqm numeric, steps_en text[], steps_hi text[],
        ferment_days int null, shelf_life_days int null,
        apply_every_days int null, apply_method text, safety_notes_en, safety_notes_hi, status)
rules(id, code unique, description, params jsonb, applies_to text, status) -- engine rules, section 7
library_chunks(id, source_table, source_id, lang, text, embedding vector(1024), status)
```

### Seed list for v1 (about 60 crops, Malwa)

| Layer / role | Crops |
| --- | --- |
| Underground | Ginger, turmeric, carrot, radish, beetroot, onion, garlic, sweet potato, colocasia (arbi) |
| Surface (leafy) | Spinach, methi, coriander, amaranth, lettuce, mint, dill, mustard greens, chaulai |
| Middle | Tomato, brinjal, chilli, capsicum, okra, cabbage, cauliflower, knol-khol, cluster bean, bush beans, marigold |
| Climber | Bottle gourd, ridge gourd, sponge gourd, bitter gourd, cucumber, pointed gourd (parwal), ivy gourd (kundru), pole beans, peas, sem |
| Canopy / short fruit | Papaya, banana, drumstick (moringa) |
| Orchard | Mango, guava, custard apple, lemon, pomegranate, jamun, amla, dragon fruit |
| Rotation field | Soybean, moong, urad, chana, wheat, kodo / kutki millet, mustard |
| Border | Lemongrass, curry leaf, karonda, bamboo, vetiver |
| Green manure | Dhaincha, sunn hemp |

### Example record (illustrative values; agronomist must verify before approval)

```json
{
  "slug": "bottle-gourd", "name_en": "Bottle gourd", "name_hi": "लौकी",
  "family": "cucurbit", "category": "vegetable",
  "layers": ["climber"], "seasons": ["kharif", "zaid"],
  "sow_windows": [{"from": "02-01", "to": "03-15", "method": "direct"},
                  {"from": "06-15", "to": "07-31", "method": "direct"}],
  "days_to_first_harvest": 60, "harvest_span_days": 60,
  "spacing_plant_cm": 90, "height_max_cm": 250,
  "sun": "full", "water_need": "medium", "terrace_ok": true,
  "min_container_depth_cm": 45, "status": "draft"
}
```

### Review workflow

1. Anyone with the agronomist role creates or edits an entry → `draft`.
2. Submit → `in_review`; a different agronomist (or the same one after 24 hours for v1) approves → `approved`.
3. On approval, regenerate that entry's `library_chunks` (en + hi) and embeddings.
4. Plans record `engine_version` and library entry versions used, so a later library change never silently alters an active plan; the owner is offered "update plan" instead.
5. Prices have `price_updated_on`; the UI shows "prices older than 90 days" when stale.

## 7. Design engine

The engine is deterministic and rule-based: the same inputs and library version always give the same plan. The LLM only explains the result in plain language afterwards. Target: under 10 seconds for 2 acres.

### Pipeline

1. **Validate** the polygon: simple (no self-intersection), 5 sqm ≤ area ≤ 20,250 sqm (5 acres; MVP cap), no side shorter than 1 m. Reject with a specific error code (section 12).
2. **Project** to UTM 43N (EPSG:32643) for all metric work; convert back to WGS84 for storage.
3. **Subtract obstacles** (trees, tank, stairs, existing structures) with a 0.5 m buffer.
4. **Orient:** true north = map north corrected by `north_bearing_deg`. Compute the minimum rotated rectangle to find the plot's main axis.
5. **Pick a template** by site type and area (table below).
6. **Carve zones** in this order: border → north strip (tall zone) → water → utility and nursery → beds → rotation.
7. **Lay out beds** inside the beds zone.
8. **Assign crops to layers** per bed and season.
9. **Check water and load;** adjust.
10. **Estimate** costs, yields and income; build the plan summary.
11. **Verify invariants** (section 5) and save as a `draft` plan.

Before choosing a template, the engine loads the farm's site profile (section 17): confirmed soil, drainage, slope, climate normals, groundwater class, local mandi prices and transport cost replace generic defaults in every rule below. Crop value uses local net price (median mandi or direct price minus transport cost); the water penalty doubles when the groundwater class is critical or over-exploited.

### Templates and zone shares

| Template | Applies when | Beds | Orchard / canopy | Rotation | Border | Water | Utility + nursery | Paths |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| T — terrace | `site_type = terrace` | 55% (planters) | in drums on edges | — | — | tank only | 10% | 35% |
| S — small plot | ground, < 150 sqm | 65% | 12% | — | 10% | tank only | 13% | inside beds zone |
| M — medium | 150–2,000 sqm | 45% | 20% | — | 10% | 5% | 12% | 8% |
| L — large | 2,000–20,250 sqm | 35% | 25% | 20% | 8% | 7% | 5% | inside zones |

Shares are defaults in `rules`; the owner can adjust each zone ±10 percentage points in the editor, and the engine re-runs.

### Zone placement rules

- **Border:** inward buffer of the parcel boundary. Width: S 0.6 m, M 1.0 m, L 2.0 m. Skip the gate segment (user marks the gate; default = the south-most edge midpoint).
- **North strip (orchard, canopy, utility):** split the remaining polygon with a line perpendicular to true north; binary-search the line offset until the northern piece matches the target area ±2%. Tall crops (height > 2 m) may only be placed here.
- **Water:** at the lowest point if `slope_dir` is set, else adjacent to the utility zone. Pond size = 30 days of peak-month demand, capped by the zone share; for S and T it is a tank, not a pond.
- **Utility and nursery:** nursery adjacent to the gate; utility (compost, drums) adjacent to water and away from the gate if space allows.
- **Rotation field (L only):** the largest remaining rectangle-like piece away from the north strip.
- If a zone cannot fit, drop zones in this order and record a warning: rotation → water pond (fall back to tank) → orchard (fall back to canopy crops in beds).

### Bed layout rules

- Default bed width 1.2 m, path 0.6 m, max bed length 10 m (a cross path of 0.6 m every 10 m); all from `settings`.
- Bed long axis runs north–south (±15°). If the beds zone is narrower than 3 m in that direction, run beds along the zone's main axis instead and record a warning.
- Tile rectangles across the zone, clip to the zone, drop pieces under 2 sqm or narrower than 0.9 m. Number beds B1, B2... from the gate side.
- Raised beds (`raised = true`) when `drainage = waterlogs` or soil is black / clay.
- Mark beds for a trellis (`has_trellis`) in alternate rows so climbers do not shade each other; trellis height 2.1 m.

### Terrace rules (template T)

- `terrace_load_kg_per_sqm` is mandatory; show a blocking notice asking the owner to get it from a structural engineer.
- Allowed media depth (m) = (load × 0.8) ÷ wet media density (default 550 kg/m³ for a cocopeat mix; `settings`). Cap container depth at this value; crops needing deeper containers are excluded.
- Heavy planters only within 1 m of the parapet; the centre is paths and light grow bags. Canopy plants only in drums in corners. No pond.

### Crop assignment

For each bed and each season covered by the plan (12 months from `start_date`), fill layers underground → surface → middle → climber (climber only on trellis beds).

**Hard constraints (a candidate is rejected if any fails):**

- Status `approved`; season and sow window reachable from the start date.
- Layer allowed for the crop; height fits the zone rule.
- Terrace: `terrace_ok` and container depth ≥ `min_container_depth_cm`.
- `drainage = waterlogs` → only `waterlogging_tolerant` crops unless the bed is raised.
- No `avoid` companion pair within one bed in the same season.
- Rotation: no crop of the same `family` in the same bed in consecutive seasons.

**Score** = 0.4 × value + 0.3 × diversity + 0.2 × ease − 0.1 × water. Weights come from `rules` and shift with the goal: `income` raises value to 0.55; `home_food` raises diversity to 0.45.

- value = expected yield per sqm × direct price, normalised 0–1 across candidates.
- diversity = 1 if the crop is not yet used elsewhere in the plan this season, else 0.3.
- ease = 1 for low-care crops (library flag), else 0.5.
- water = normalised water need.

Select greedily with a fixed tie-break (crop slug) so results are reproducible. Require at least 6 distinct crops per season for M and L, 4 for S and T.

### Quantities, water and estimates

- Plant count per layer = floor(bed length ÷ plant spacing) × rows that fit the bed width.
- Expected yield = bed area × `expected_yield_kg_per_sqm` × layer factor (multilayer crowding factor from `rules`, agronomist-set; default 0.7 for underground and surface, 0.8 for middle and climber).
- Peak water demand = sum over plantings of area × stage water. If it exceeds `water_summer_lpd`, swap the highest-water crops for lower ones in zaid until it fits; if still over, warn.
- Setup cost = zone area × cost per sqm by zone kind (`settings`, INR) plus fixed items (tank, drip kit). Every money figure in the summary is labelled "estimate".

### Engine output (stored in `plans.summary` and child tables)

```json
{
  "engine_version": "1.0.0",
  "template": "M",
  "area_sqm": 74.3,
  "zones": [{"kind": "beds", "area_sqm": 33.4, "bed_codes": ["B1", "B2", "B3"]}],
  "beds": [{"code": "B1", "length_m": 7.3, "width_m": 1.2, "raised": true, "has_trellis": true,
            "layers": {"rabi": {"underground": "carrot", "surface": "spinach", "middle": "tomato", "climber": "peas"}}}],
  "water": {"peak_lpd": 310, "available_lpd": 500, "ok": true},
  "estimates": {"setup_paise": 4200000, "yearly_cost_paise": 900000, "yearly_yield_kg": 380},
  "warnings": [{"code": "BEDS_ALONG_MAIN_AXIS", "message_key": "warn.beds_axis"}]
}
```

**Golden tests:** keep 10 reference parcels (rectangle, L-shape, triangle, narrow strip, terrace, 800 sq ft Bijalpur-style plot, 1 acre, 2 acres irregular, plot with a tree obstacle, waterlogging plot) with expected outputs reviewed by the agronomist. Any engine change must pass them or update them with review.

## 8. Planner and tasks

When the owner activates a plan, the planner creates one planting per bed-layer-season and a dated task list for the next 12 months; it regenerates the next 8 weeks nightly so changes flow in.

### Planting dates

- `planned_sow` = the first date ≥ plan start inside the crop's sow window; if `nursery_days` is set, a nursery sowing task comes `nursery_days` earlier and the bed task becomes "transplant".
- `planned_harvest_start` = sow + `days_to_first_harvest`; `planned_harvest_end` = start + `harvest_span_days`.
- Stagger leafy crops: split a leafy layer into 2–3 sowings 14 days apart (setting) so harvest is continuous.

### Task types

| Type | Generated when | Default window | Notes |
| --- | --- | --- | --- |
| `prepare_bed` | 7 days before first sowing in a bed | 5 days | Includes compost quantity: 3 kg/sqm default (setting) |
| `nursery_sow` | sow date − `nursery_days` | 2 days | Tray count from plant count + 20% |
| `sow` / `transplant` | planned sow date | 3 days | Quantity and spacing in params |
| `mulch` | 3 days after sowing | 3 days |  |
| `install_trellis` | 10 days after climber sowing | 5 days | Only beds with `has_trellis` |
| `apply_recipe` | every `apply_every_days` per recipe (e.g. jeevamrut 15 days) | 2 days | Linked prep task (`prepare_recipe`) created `ferment_days` earlier |
| `pest_check` | weekly per active bed | 2 days | Asks for a photo if anything looks wrong |
| `harvest` | weekly from harvest start to end | 2 days | Reply collects kg |
| `clear_bed` | day after harvest end | 3 days | Triggers next season's `prepare_bed` |
| `weather_action` | from alerts (section 9) | 1 day | E.g. "cover greens with shade net" |
| `manual` | owner creates | owner sets |  |

Watering is not a daily task (it would spam users); it appears as a standing instruction in the weekly digest, with litres per bed from the engine. A weekly `water_check` task asks "is drip reaching all beds?".

### Batching and status

- Tasks are sent in two batches: a weekly digest (Sunday 18:00 IST) and a daily list (07:00 IST) of tasks whose window starts that day. Max 8 tasks per daily message; the rest are summarised with a link.
- A task not done by `due_date + window_days` becomes `overdue`; owners get one overdue summary per day, never per task.
- `idempotency_key` = `farm_id:type:planting_id:due_date`; regeneration upserts on it and never duplicates or revives cancelled tasks.

### Rescheduling rules

- **Missed sowing:** if still inside the sow window, move to the next day and re-send; if the window has closed, mark the planting `skipped` and propose the best alternative crop for that layer from the engine (owner approves in one tap).
- **Crop failure** (caretaker reports "failed" or photo check says severe): planting → `failed` with reason; offer a replacement if a sow window is open within 21 days.
- **Early or late harvest reported:** shift that planting's later harvest tasks and `clear_bed` accordingly.
- **Weather:** heavy rain forecast moves `sow`, `apply_recipe` and `mulch` tasks out of the rain days; heat alerts add shade tasks.
- Every reschedule writes an `audit_log` entry with the reason, shown to the owner as "Changed because...".

The weather rescheduling rule above is post-MVP (it depends on forecast alerts).

### Shopping list (MVP)

- Generated per season from the plan's plantings and due recipes, and regenerated whenever the plan changes.
- Items: seeds or seedlings (plant count + 20% buffer), saplings, compost (kg by bed area), mulch, recipe ingredients (jaggery, besan, neem), and drip parts and tank at setup.
- Each item shows quantity, unit, approximate cost from the regional rate table, and the nearest source from `places` (section 17).
- Stored in `shopping_lists(id, plan_id, season, items jsonb, generated_at)`; the owner can tick items as bought, and ticked items can create a cost log in one tap.

## 9. Records, profit and weather alerts

Every number on the owner's dashboard traces back to a `logs` row or a plan estimate, and the UI always labels which is which.

### Logging

- Harvest: bed (required), crop (defaults to what's in that bed), quantity + unit; converting bunch or piece to kg uses a per-crop factor in the library (optional).
- Cost: amount, category (`seed`, `input`, `labour`, `water`, `transport`, `tools`, `setup`, `other`), optional bed, optional photo of the bill.
- Sale: crop, quantity, amount, buyer type (`household`, `shop`, `restaurant`, `mandi`, `other`).
- Photo / issue / note: optional bed; an issue photo triggers the photo check (section 11).
- Offline logs carry `client_uuid`; the server ignores duplicates.
- Logs can be edited by their creator for 48 hours and by the owner anytime; every edit goes to `audit_log`.

### Calculations

```text
revenue(period)          = Σ sale.amount
home_use_value(period)   = (Σ harvest.kg − Σ sold.kg) × crop.price_direct   -- shown separately, never mixed into revenue
running_cost(period)     = Σ cost.amount where category ≠ 'setup'
setup_amortised(period)  = Σ setup costs ÷ amortisation_years (setting, default 5), pro-rated to the period
profit(period)           = revenue − running_cost − setup_amortised
zone_profit              = same, filtered by bed → zone; unassigned costs split by zone area share
plan_vs_actual(planting) = Σ harvest.kg ÷ expected_yield_kg   -- green ≥ 0.8, amber 0.5–0.8, red < 0.5
payback_month            = first month where cumulative profit incl. full setup ≥ 0
```

Periods: this week, this month, this season (kharif Jun–Oct, rabi Nov–Mar, zaid Mar–Jun), last 12 months, since start. Money is stored in paise and computed in integers; display rounds to rupees.

### Weather alerts (post-MVP)

A daily job at 05:30 IST fetches the Open-Meteo 7-day forecast once per 0.1° grid cell (farms share cells), stores a snapshot, and evaluates rules. Thresholds are defaults in `settings`, to be tuned with the agronomist.

| Alert | Trigger (default) | Actions |
| --- | --- | --- |
| Heat | Max temp ≥ 42 °C on any of the next 3 days (severe ≥ 45 °C) | Shade net on leafy beds, water early morning, mulch check |
| Heavy rain | ≥ 50 mm forecast in a day | Move sowing and recipe tasks, clear drainage, check raised beds |
| Strong wind | Gusts ≥ 40 km/h | Check trellis ties; terrace: secure shade net and light pots |
| Cold | Min temp ≤ 4 °C | Cover nursery and tender seedlings overnight |
| Dry spell | No rain for 10 days in Jul–Sep | Irrigation check, mulch |

- Max one alert message per farm per day; combine multiple alerts into one. Severe alerts can send immediately.
- Each alert creates `weather_action` tasks and reschedules tasks as in section 8.
- If Open-Meteo is unreachable, retry 3 times with backoff; after that, skip alerts for the day and log an error, never send stale warnings.

## 10. WhatsApp messaging

The messaging app is the caretaker's whole interface, so every flow must work with buttons and short replies in Hindi, with typing as a fallback. Flows are written once against a \`Channel\` interface (send text, send buttons, send list, receive reply, download media): the beta runs on the Telegram Bot API (free, inline keyboard buttons, no template approval), and WhatsApp Cloud API is added later as a second implementation. The WhatsApp rules below apply once it is switched on.

### Platform rules to respect (Meta WhatsApp Cloud API)

- Business-initiated messages outside the 24-hour customer-service window must use **pre-approved templates**; free-form and interactive messages only inside the window. Track `wa_sessions.last_inbound_at`.
- Get explicit **opt-in** when a caretaker is invited; honour "STOP" / "बंद" immediately (set `wa_opt_out`).
- Verify every webhook with `X-Hub-Signature-256` and the app secret; dedupe on `wa_message_id`; respond 200 within 5 seconds and process via the queue.
- Media (photos, voice) arrive as media IDs: download immediately to S3, since media URLs expire.
- Pricing is per message and changes over time; log every outbound message with its template name so costs can be reported. Check current Meta pricing before launch.

### Templates (register in both `en` and `hi`)

| Template | When | Quick-reply buttons |
| --- | --- | --- |
| `invite_caretaker` | Owner invites a caretaker | Join / Not now |
| `daily_tasks` | 07:00 IST, if tasks exist | All done / Some not done / Help |
| `weekly_digest` | Sunday 18:00 IST | Open plan (link) |
| `harvest_prompt` | On harvest days | Log harvest / No harvest today |
| `weather_alert` | From section 9 | OK, done / Need help |
| `overdue_summary` | Owner only, daily if overdue | Open app (link) |

Keep templates short (under 300 characters of body), with bed codes and crop names in the user's language; long lists go behind a link.

### Conversation flows (state machine in `wa_sessions.state`)

1. **All done** → mark all of today's sent tasks `done`, reply with a one-line thanks and tomorrow's count.
2. **Some not done** → send an interactive list (max 10 rows) of today's tasks; each selection toggles done / not done; a "Finished" button closes it. Unselected tasks stay pending.
3. **Log harvest** → ask "Which bed?" as a list of beds with harvest tasks → "How much?" with buttons (1 kg / 2 kg / 5 kg / Type amount) → confirm.
4. **Free text** is parsed: patterns like `B2 lauki 3 kg`, `बी 2 लौकी 3 किलो`, `seed 250 rs`. Parser order: regex rules → Hindi/English number and unit normalisation → LLM extraction with a strict JSON schema → if confidence < 0.8, ask a confirm question with buttons.
5. **Photo** → ask "Which bed?" (list) → store as `photo` log → run photo check (section 11) → reply with the result and any recipe task added.
6. **Voice note** → store in S3 as a `note` log, reply "Saved; your owner can listen to it". (Transcription is post-MVP.)
7. **Help** or any question → route to the AI helper with the farm context; answers capped at about 600 characters with an "Open in app" link for more.
8. **Unknown sender** → reply with a short explanation and no data access.

Retries: failed sends retry 3 times over 30 minutes; after that the task stays `pending` and the owner's app shows "message not delivered".

## 11. AI helper

The AI helper explains, answers and triages; it never decides layouts, never writes to plans or the library, and says "not sure" rather than guessing.

### Uses in the MVP

1. **Plan explanation:** after the engine runs, a plain-language summary of why each zone and crop was chosen (from `plans.summary` + rule codes), in the owner's language.
2. **Q&A** from the web app and WhatsApp, grounded in the library and this farm's data.
3. **Photo check:** a plant photo in → likely issue, confidence, organic remedy from `recipes`, and whether to call an expert.
4. **Free-text parsing** for WhatsApp logs (section 10).

### Agent design (LangGraph)

Nodes: `classify_intent` → `retrieve` → `call_tools` (loop, max 4 calls) → `compose_answer` → `safety_check` → respond.

Read-only tools, all scoped to the caller's `farm_id` and role:

| Tool | Returns |
| --- | --- |
| `get_farm_summary()` | Area, template, zones, current season |
| `get_bed(code)` | Bed size, current plantings, recent logs |
| `get_tasks(range)` | Pending and overdue tasks |
| `get_weather()` | Latest 7-day snapshot and active alerts |
| `search_library(query, lang)` | Top 6 approved chunks with source IDs |
| `get_recipe(slug)` | Ingredients, quantities for the bed area, steps |
| `get_profit(period)` | Owner only; blocked for caretakers without money access |

### Retrieval

- Chunk approved library entries per crop, pest and recipe (about 300–500 tokens), one chunk per language; embed and store in `library_chunks`.
- Hybrid search: vector similarity + Postgres full-text on crop names (Hindi and English synonyms, e.g. lauki / bottle gourd / लौकी).
- Answers must cite chunk IDs internally (`ai_messages.citations`); the UI shows "Based on: Bottle gourd guide".

### Photo check (post-MVP)

- Resize to max 1,568 px, strip location metadata, send to the vision model with the bed's crop, season and recent weather.
- The model returns strict JSON: `{"issue_slug" | null, "confidence": 0–1, "observations": [], "recipe_slugs": [], "escalate": bool}`; only slugs that exist in `pests` / `recipes` are accepted.
- Confidence ≥ 0.7 → show the issue and remedy and add an `apply_recipe` task (owner can undo). 0.4–0.7 → "possibly X", suggest a closer photo. < 0.4 or `escalate` → "not sure; show this to an expert", with KVK contact from settings.

### Guardrails

- System prompt: answer only about this farm and the approved library; if the library lacks the answer, say so and suggest asking an expert. Never recommend chemical pesticides; never give dosages not in a recipe.
- `safety_check` node rejects answers that mention crops, quantities or recipes absent from the retrieved context, then retries once with a stricter instruction or returns the fallback "I don't have verified information on this yet."
- Human health, animal health, legal and financial questions get a polite redirect.
- Limits: `max_ai_messages_per_day` per user (default 30), token logging per message, prompt caching for the system prompt and library context.
- Prompts are versioned files; every `ai_messages` row stores the prompt version and model name.
- Agronomist review queue: any answer a user marks "wrong" plus a 5% random sample go to the agronomist weekly.

## 12. API endpoints

REST over JSON, prefix `/api/v1`, JWT bearer auth except where marked public. Every farm-scoped route checks `farm_members`. Geometry is GeoJSON in WGS84.

| Method | Path | Purpose | Role |
| --- | --- | --- | --- |
| POST | `/auth/otp/request` | Send a caretaker a single-use login link in their messaging app (rate limit 3 per 10 min); owners log in through Keycloak | Public |
| POST | `/auth/otp/verify` | Verify the single-use link (expires in 15 minutes), return a session token | Public |
| GET / PATCH | `/me` | Profile, language, unit preference | Any |
| POST / GET | `/farms` | Create / list my farms | Any |
| GET / PATCH / DELETE | `/farms/{id}` | Farm details | Owner (GET: members) |
| PUT | `/farms/{id}/parcel` | Save boundary, soil, water, obstacles; returns area and warnings | Owner |
| POST | `/farms/{id}/members/invite` | Invite caretaker by phone (sends WhatsApp) | Owner |
| POST | `/farms/{id}/plans/generate` | Run the engine; returns a draft plan (sync if < 10 s, else 202 + job ID) | Owner |
| GET | `/farms/{id}/plans/{plan_id}` | Plan with zones, beds, layers, summary, warnings | Members |
| PATCH | `/farms/{id}/plans/{plan_id}` | Edits: zone shares, swap a crop, rename beds (re-validates) | Owner |
| POST | `/farms/{id}/plans/{plan_id}/activate` | Activate; creates plantings and tasks | Owner |
| GET | `/farms/{id}/tasks?from&to&status` | Task list | Members |
| PATCH | `/farms/{id}/tasks/{task_id}` | Mark done / skip / reschedule | Members |
| POST | `/farms/{id}/logs` | Create a log; `client_uuid` for dedupe | Members |
| POST | `/farms/{id}/logs/batch` | Offline sync, up to 100 logs | Members |
| POST | `/farms/{id}/uploads/presign` | Presigned object-storage (S3 API) URL for a photo (max 10 MB, jpeg/png/webp) | Members |
| GET | `/farms/{id}/profit?period` | Revenue, costs, profit, per zone, plan vs actual | Owner (+ permitted caretakers) |
| GET | `/farms/{id}/alerts` | Active weather alerts | Members |
| POST | `/farms/{id}/ai/messages` | Ask the AI helper (streams via SSE) | Members |
| POST | `/farms/{id}/ai/photo-check` | Photo check for a log | Members |
| POST | `/farms/{id}/plans/{plan_id}/export` | Create PDF + share link (expires in 30 days) | Owner |
| GET | `/share/{token}` | Read-only plan view | Public (signed token) |
| GET / POST / PATCH | `/library/...` | Crops, recipes, pests, rules; submit and approve | Agronomist (GET approved: any) |
| GET / POST | `/webhooks/whatsapp` | Verify token (GET), receive messages (POST); for the beta also \`POST /webhooks/telegram\`, checked with Telegram's secret-token header | Meta (signature checked) |
| GET / PATCH | `/admin/settings`, `/admin/users` | Settings and users | Admin |

**Additional MVP endpoints:** `GET /farms/{id}/site-profile` (facts with source, date, confidence), `PATCH /farms/{id}/site-profile` (confirm or edit facts), `POST /farms/{id}/site-profile/refresh` (owner, rate limited), `GET /farms/{id}/shopping-list?season`, `PATCH /farms/{id}/shopping-list/{item}` (mark bought). **Post-MVP endpoints** (do not build now): `/ai/photo-check`, `/plans/{plan_id}/export`, `/share/{token}`, `/alerts`, `/webhooks/whatsapp`.

### Error format

```json
{"error": {"code": "PARCEL_SELF_INTERSECTS", "message_key": "err.parcel_self_intersects", "details": {}}}
```

Codes include `PARCEL_TOO_SMALL`, `PARCEL_TOO_LARGE`, `PARCEL_SELF_INTERSECTS`, `TERRACE_LOAD_REQUIRED`, `NO_CROPS_FIT`, `WATER_INSUFFICIENT` (warning), `PLAN_ALREADY_ACTIVE`, `FORBIDDEN_ROLE`, `RATE_LIMITED`, `AI_LIMIT_REACHED`. The frontend maps `message_key` to `en` / `hi` text.

Pagination: cursor-based (`?cursor&limit`, max 100). All list endpoints sort newest first unless the resource is date-based (tasks sort by due date).

## 13. Frontend

One responsive PWA serves owners on laptop and phone and caretakers who prefer an app; it must work on a mid-range Android phone over 3G.

### Screens

| Screen | Key elements |
| --- | --- |
| Login | Phone number, OTP (auto-read on Android), language switch visible before login |
| Farm setup wizard | 1. Site type (ground / terrace) → 2. Draw boundary on satellite map, or enter side lengths for a rectangle, or upload KML → 3. Mark gate and obstacles → 4. Soil, drainage, slope (pictures for each option, "not sure" allowed) → 5. Water source and summer availability → 6. Goal, budget, labour → review. Progress saved after every step. |
| Plan view | Scaled map of zones and beds (colour by zone kind, pattern for trellis beds), north arrow, scale bar; tap a bed → layers per season; side panel: summary, costs, warnings, AI explanation |
| Plan editor | Zone share sliders (±10 points), swap crop in a layer (only valid candidates listed), rename beds; "Regenerate" shows a diff before saving |
| This week | Tasks grouped by day and bed; one-tap done; overdue on top; filter by bed |
| Log | Big buttons: Harvest / Cost / Sale / Photo / Note; bed picker; number pad; works offline |
| Money | Period switcher; revenue, costs, profit; per-zone cards; plan-vs-actual per planting (green / amber / red); payback estimate |
| Ask | Chat with the AI helper; photo button; sources shown under answers |
| Team | Invite caretaker by phone, toggle money visibility, see message delivery status |
| Library (agronomist) | Table of crops with status; edit form with validation; approve button; review queue of flagged AI answers |

**Setup wizard in the MVP (shorter):** 1. Site type → 2. Pin location and draw or enter the boundary → 3. Mark gate and obstacles → 4. **"We found for your land" card** from site intelligence, where the owner confirms or changes each fact; soil, drainage and slope questions appear only when confidence is low or the owner taps Change → 5. Water source and summer availability → 6. Goal, budget, who works → review. **Also add a Shopping list screen:** season switcher, items with quantity, rough cost, nearest source, and a "bought" tick.

### Map and drawing details

- MapLibre GL with a satellite base layer (check the tile provider's licence and usage limits); Terra Draw for polygons with vertex editing and snapping.
- Show live area in the user's unit while drawing; warn when self-intersecting.
- Offer "enter measurements" for users who can't use a map: rectangle (length × width) or four sides + one diagonal.
- Bijalpur-style small plots: allow zoom to 0.5 m precision; show a 1 m grid.

### Offline behaviour

- Service worker caches the app shell, active plan, next 14 days of tasks and bed list.
- Logs and task updates made offline go to an IndexedDB queue with `client_uuid`; sync on reconnect via `/logs/batch`; show a "3 items waiting to sync" badge.
- Photos queue locally, compressed to max 1,600 px and about 300 KB before upload.
- Conflict rule: server wins for plans; for tasks, the latest `done_at` wins.

### Language, units and accessibility

- Hindi and English complete from day one; every string is an i18n key; crop names come from the library in both languages.
- Units follow `unit_pref`; bigha shows only if the user has set `bigha_sqft` (bigha size differs by region).
- Minimum 16 px text, 44 px touch targets, icons with labels, high contrast (outdoor use in sunlight).
- Numbers in Indian format (1,00,000); dates as "28 Sep" / "28 सितंबर".

## 14. Non-functional requirements, security and testing

The MVP must be reliable enough that a caretaker trusts the morning message; correctness of plans and tasks matters more than feature count.

### Performance and reliability targets

| Area | Target |
| --- | --- |
| Plan generation | < 10 s for 2 acres; < 3 s for under 1,000 sqm |
| API p95 latency (non-AI) | < 400 ms |
| AI answer first token | < 4 s |
| PWA first load on 3G | < 5 s; repeat load < 2 s |
| Daily task messages | 99% delivered by 07:15 IST |
| Uptime | 99.5% monthly (API) |
| Backups | Nightly pg\_dump + restic to a free-tier bucket, encrypted, 14-day retention; monthly restore test |

### Security and privacy

- OWASP basics: input validation with Pydantic, parameterised queries only, CORS locked to the app domain, rate limits on auth, AI and uploads.
- Keycloak tokens: access 15 minutes, refresh 30 days, rotated and revocable. Caretaker link tokens are single-use, signed, and expire in 15 minutes.
- Row-level authorisation in a single dependency (`require_farm_role`) used by every farm route; tests prove a caretaker cannot read money or another farm.
- Object storage private; photos served by short-lived signed URLs; strip EXIF location from photos before sending to the LLM.
- Encrypt the server disk, backups and object storage at rest; TLS in transit via Caddy. Secrets only in .env files outside the repo with restricted permissions; firewall open only on 80/443 and SSH (key-only).
- Personal data: phone, name, farm location. Comply with India's Digital Personal Data Protection Act: consent at signup, a privacy notice in Hindi and English, account and data deletion on request within 30 days, and no selling of farm data.
- Send only the minimum farm context to the LLM; no phone numbers or names in prompts.

### Observability

- Structured logs with `request_id`, `farm_id`, `user_id`; GlitchTip (self-hosted, Sentry-compatible) for errors; Uptime Kuma and alert rules on job failures, message send failure rate > 5%, and AI error rate > 5%.
- Product events (for the MVP metrics): plan\_generated, plan\_activated, task\_done, log\_created, ai\_question, photo\_check, message\_delivered.

### Testing

- **Unit:** geometry helpers, template choice, zone carving, bed tiling, crop constraints, scoring, date calculations, profit formulas, WhatsApp text parser (100+ Hindi and English examples).
- **Golden layout tests:** the 10 reference parcels from section 7, compared on zone areas (±2%), bed count, and crop assignments.
- **Property tests (Hypothesis):** random valid polygons never produce beds outside the parcel, overlapping zones, or beds narrower than 0.9 m.
- **Integration:** API with a real Postgres + PostGIS in Docker; WhatsApp webhook with recorded payloads; Open-Meteo mocked.
- **AI evaluations:** 50 question set (Hindi and English) with agronomist-approved expected facts; pass if ≥ 90% factual and 0 unsafe recommendations; run on every prompt or model change.
- **End to end:** Playwright for the setup wizard → plan → activate → log → money flow on a mobile viewport.

### Acceptance criteria for the MVP

- [ ] An owner can draw an irregular plot, get a valid plan in under 10 seconds, and understand it (AI explanation in Hindi and English).
- [ ] The agronomist rates at least 9 of 10 golden plans "correct and usable".
- [ ] A caretaker who has never used the app can complete a week of tasks and log a harvest only through WhatsApp.
- [ ] Offline logs made on the PWA sync without duplicates.
- [ ] Missed sowing and crop failure each reschedule tasks correctly with a visible reason; the site profile auto-fills and every fact can be confirmed or changed (section 17).
- [ ] Profit and plan-vs-actual match a hand calculation on a test farm to the rupee.
- [ ] A caretaker without money access cannot see any sale or profit figure via app, API or AI helper.

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

## 17. Site intelligence

From just the location and boundary, the platform collects the site facts a user usually can't answer (soil, climate, water stress, slope, market prices, distances, nearby places), shows each with its source and confidence, and asks the owner to confirm. The owner's answer always wins.

### Flow

1. Saving the parcel queues `site_profile.build(farm_id)`: all data adapters run in parallel with a 20-second overall budget; partial results are fine.
2. Each result is stored as a `site_facts` row with source, method, date and confidence.
3. The wizard shows a "We found for your land" card grouped as Soil and land, Climate, Water, Markets, Nearby. Each item offers: Looks right / Change / Not sure.
4. Confirmed or edited values are saved with source `user`. Priority when reading: user-entered → soil test → derived (newest first).
5. Facts that change the plan (soil, drainage, water) with confidence below 0.5 are asked directly as wizard questions.
6. Refresh cadence: mandi prices weekly; climate normals and groundwater class yearly; soil, elevation and land cover once; places monthly.

### Facts collected in the MVP

| Fact | Default source (via adapter) | Method | Confidence | Used by |
| --- | --- | --- | --- | --- |
| Region / agro-climatic zone | District boundaries + curated district → region table | Point in polygon | High | Crop library, templates |
| Climate normals: monthly rain, max and min temperature, hottest and coldest months, monsoon onset | Open-Meteo historical weather (last 10 years) | Monthly aggregates | High | Sowing windows, crop filter, water plan |
| Soil texture, clay %, pH, organic carbon (0–30 cm) | ISRIC SoilGrids (about 250 m) | Average over parcel, texture → `soil_type` | Medium; always labelled "likely" | Soil defaults, raised beds, crop filter |
| Elevation, slope, lower side | Copernicus DEM GLO-30 | Slope around the parcel | Medium; "unknown" for plots smaller than the data grid | Pond placement, drainage |
| Land cover within 500 m | ESA WorldCover (10 m) | Share of cropland, built-up, trees | Medium | Urban vs rural hints, spray-drift note |
| Groundwater stress class | Central Ground Water Board block categories (curated yearly table) | Block lookup | High, but block-level | Water warnings, water penalty in crop scoring |
| Mandi prices per crop | Agmarknet daily prices via data.gov.in (ingested into `mandi_prices`) | Median modal price over the last 12 months, same-season months, 3 nearest mandis that report the crop | Medium; fallback to state median, then library default | Crop value score, income estimates |
| Distance and drive time to nearest mandis, nearest town, Indore city | OSRM routing on OpenStreetMap (self-hosted) | Road distance and time | High where roads are mapped | Transport cost, direct-sale feasibility |
| Transport cost per kg to each market | Rate table in `settings` (Rs per km per quintal) | Distance × rate | Medium | Net price after transport |
| Nearby places: KVK, nurseries, input shops, gaushalas, cold storage, FPOs | Curated `places` table for the Indore region + OpenStreetMap | Top 3 of each within 25 km | Curated high; OSM low | Shopping list sources, AI answers |
| Possible subsidies (drip, solar pump, horticulture) | Curated `schemes` table by state and district | Simple rules | Medium; "check with the office" | Note beside setup cost; never subtracted automatically |
| Local daily wage and common input prices | Curated regional rates; later refined from users' cost logs | Lookup | Low to medium | Running cost estimate |

### Tables

```sql
site_facts(id, farm_id, key text, value jsonb, unit text null,
           source text,                 -- 'open_meteo','soilgrids','dem','worldcover','cgwb','agmarknet','osrm','places','user','soil_test'
           method text, confidence numeric, fetched_at timestamptz, expires_at timestamptz,
           status text check (status in ('derived','confirmed','edited','rejected')),
           unique(farm_id, key, source))
-- view site_profiles: one winning value per farm and key (user > soil_test > derived, newest first)
mandis(id, name, district, state, geom geometry(Point,4326), agmarknet_code, region_id)
mandi_prices(id, mandi_id, crop_id, price_date date, min_paise, max_paise, modal_paise, unit)
places(id, kind text, name, name_hi, geom geometry(Point,4326), phone null, source text, verified bool, region_id)
schemes(id, region_id, name_en, name_hi, applies_to text, rule jsonb, office text, url text, checked_on date)
geo_cache(cell_key text, source text, payload jsonb, fetched_at timestamptz, primary key(cell_key, source))
```

### Rules

- Every source is an adapter implementing `fetch(parcel) -> list[Fact]`, with a fake for tests, registered in the "site data sources" registry (section 16). A failing adapter returns nothing and logs; it never blocks setup.
- Cache results by 0.01° grid cell and source so nearby farms reuse them; respect each source's rate limits and licence, store its attribution, and show attributions on the site profile screen.
- Refreshes never overwrite `confirmed` or `edited` facts; if new derived data differs a lot, show "new data available" to the owner.
- Sanity ranges reject implausible values (e.g. annual rain below 100 mm or above 5,000 mm for MP) and mark them low confidence.
- Soil facts always carry "estimated from public data; confirm with a Soil Health Card test", and a test result, once entered, replaces them.
- Mandi prices ingest as a scheduled job into our own tables; plans read our tables, never the live API.

### Acceptance for this module

- [ ] For 10 test locations around Indore (including an urban Bijalpur plot, 4 villages 30–70 km away and a terrace), a profile builds in under 20 seconds with climate, soil, 3 mandis and distances.
- [ ] Every fact shows its source and date; changing any value regenerates the plan with it.
- [ ] With every adapter switched off, setup still completes using wizard questions.
