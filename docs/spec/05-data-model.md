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

