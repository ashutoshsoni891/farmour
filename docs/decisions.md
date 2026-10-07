# Decisions

Record every structural choice: context, decision, consequences. Newest first. Template:

## YYYY-MM-DD — Title
- **Context:**
- **Decision:**
- **Consequences:**

---

## 2026-10-02 — Onboarding 2.0, interactive plot, Google satellite, AI agronomist
- **Onboarding is 2 screens:** where ("I'm on my land" GPS, search, typed coordinates, tap or
  drag the pin; terrace is a checkbox) and how big (one number in sq ft/acre/bigha; we save a
  square at the pin). Defaults: goal both, who works self, water unknown, drainage never asked.
  The farm page shows plain-language insights (only statements the data or a spec rule supports)
  and an optional "Improve your plan" card (water, who works, goal, soil) that saves on one tap.
- **Plot editing:** a saved plot (even the auto square) opens on the map as an editable shape:
  drag corners, drag midpoints to add corners, drag the whole shape; or paste corner points
  ("lat, long" per line). Coordinates are rounded to 8 decimals for Terra Draw.
- **Satellite:** Google Map Tiles API (2D satellite) on the MapLibre map, default when
  `GOOGLE_MAPS_KEY` is set at build time; session token cached per language, Google logo and
  per-viewport imagery credit shown; street map when no key. The key is public in the browser:
  restrict it to the app's domains and to the Map Tiles API in Google Cloud.
- **AI agronomist (agreed, not built yet):** hybrid. The rule engine decides; AI drafts cited
  library values (new status `ai_verified`, usable only behind `library.allow_ai_verified` with a
  "not yet reviewed by an expert" label), explains plans and turns owner wishes into preferences.

## 2026-10-02 — M2b site intelligence choices
- **Flow:** saving a parcel publishes `parcel.saved`; the outbox subscriber only enqueues a Celery
  task (`site.build_profile`, via `app/core/queue.py`, so modules never import the jobs layer). The
  worker runs the sources in parallel with a 20 s budget (3 s kept for local lookups and routing),
  caches results per 0.01° cell and source in `geo_cache`, and never overwrites a fact the owner
  confirmed or edited. Facts keep source, method, date, confidence and attribution.
- **Sources now:** Open-Meteo (10-year climate normals; elevation + slope from 5 points ~90 m
  apart, low confidence for plots smaller than the DEM cell), SoilGrids (texture, pH, organic
  carbon; texture and the extras are separate requests because the extras are slow; the public API
  allows about 5 calls/minute, so the cell cache matters), OpenStreetMap via Overpass (input shops,
  nurseries, cold storage; low confidence), a curated district -> region table (Malwa districts),
  and self-hosted OSRM for road distance to Indore and to the 3 nearest mandis.
- **Honest gaps:** groundwater class has a table but no data yet (no cited CGWB figures; the row
  stays absent, never guessed); mandi prices need `DATA_GOV_IN_API_KEY` (ingest is skipped without
  it); when OSRM is down distances are labelled "estimated, straight line x 1.3" (setting
  `site.road_factor`); no `schemes` table, no WorldCover, no transport-rate (spec gives no value).
- **Soil/drainage questions:** asked only when soil is missing or low confidence (below
  `site.low_confidence`, 0.5), and drainage only when soil is clay/black or unknown. Answers are
  copied onto the parcel for the design engine.
- **Routing:** OSRM runs from the openstreetmap.fr Madhya Pradesh extract (~140 MB). The Geofabrik
  Central Zone file (~350 MB) ran out of memory on an 7.5 GB Docker host while building the graph.
  Optional compose profile `routing`; first prepare takes several minutes.
- **District lookup:** the wizard always resolves the district in English ("Indore"), because Hindi
  place search returns "इन्दौर ज़िला", which cannot match the region table.
- **Schedule:** daily mandi ingest at 06:30 IST; a few new mandis are geocoded per run (Nominatim).

## 2026-10-01 — M2a setup wizard choices
- **Lean wizard (3 steps now, site-data card in M2b):** where (search or pin + ground/terrace) →
  plot size (type length × width, draw on map, or four sides + diagonal) → three taps (water,
  goal, labour). Gate defaults to the south edge, obstacles and budget are left to the plan editor,
  May water is "not sure" by default. Plots are saved per step; `/setup/:farmId` resumes.
- **Parcel limits** live in setting `parcel.limits` (5 sq m to 20,250 sq m, shortest side 1 m).
  Metric work is done in EPSG:32643; the live area while drawing is geodesic (turf), so it can
  differ from the saved area by well under 1%.
- **Place search** goes through the API (`/geo/search`, `/geo/reverse`) to Nominatim with an
  identifying User-Agent (`GEOCODER_USER_AGENT`), 1 request/second and a cache; set a real contact
  in `.env`. Swap to a self-hosted Nominatim/Photon through `NOMINATIM_URL`.
- **Map:** MapLibre with OpenFreeMap streets; satellite is off unless `VITE_SATELLITE_TILES_URL`
  is set at build time (licence check before commercial use). The MapLibre worker is bundled as
  a file so the strict Content-Security-Policy needs no `unsafe-inline`; the policy is applied to
  app pages only (Keycloak sends its own).
- **Not yet:** the 1 m grid at high zoom, obstacle/gate marking, and the site-data card (M2b).

## 2026-10-01 — M1 crop library choices
- **Crop values:** the 65 crops are seeded as drafts with names, taxonomy, category and layer only.
  Every agronomy value is empty (`TODO(agronomist)`); a research pass with cited public sources
  was started but cut (plan session limit), so values arrive later in small batches or from the
  agronomist. Recipes are name-only shells; no pests are seeded (no cited source yet).
- **Categories:** added `oilseed` (mustard) to the §6 list; orchard, rotation, border and
  green-manure crops have no bed layer (`layers = []`).
- **Review gate:** submit needs the §7-required fields filled and every agronomy value to carry a
  source (link or written note); sow windows are per region (`crop_regional`), required for the
  region in setting `library.default_region` (malwa). Prices stay empty until the M2 mandi ingest.
- **Approval:** a different agronomist, or the submitter after `library.self_approve_after_hours`
  (24). Editing an approved/in-review entry sends it back to draft; each approval stores a
  `library_revisions` snapshot and publishes `library.approved` (AI re-embedding lands in M7).
- **Engine rules** (zone shares, bed sizes, score weights, crowding, limits) are seeded as draft
  `rules` from the numbers the spec itself gives in §7.
- **Dev:** `~/.farm-local.env` holds the local stack secrets (outside the repo);
  `backend/scripts/dev_login.py` makes test users and tokens for the local stack.

## 2026-09-30 — M0 review fixes (architecture + security review)
- **Context:** Reviews of M0 found issues that break login and outbox delivery, and several
  auth weaknesses.
- **Decisions:**
  1. OIDC callback is `/login/callback` (Caddy sends all of `/auth/*` to Keycloak). Realm
     redirect URIs are exact, not wildcards.
  2. Caddy proxies only `/auth/realms/farm/*`, `/auth/resources/*`, `/auth/js/*`; everything
     else under `/auth` is 404. A Content-Security-Policy is set.
  3. Link login (caretaker sessions) is only for accounts without Keycloak, admin or agronomist
     roles; those must use Keycloak.
  4. `PATCH /me` no longer edits `phone`; phone is set by the messaging binding (M5).
  5. Only Keycloak-verified emails are stored; `make-admin` refuses ambiguous matches.
  6. Staging/prod refuse to boot with a weak or placeholder `LINK_SIGNING_SECRET`.
  7. Celery tasks use `standalone_session()` (unpooled engine per run); the worker imports
     every module's `events.py` so subscribers are registered.
  8. Keycloak login theme `farm` (extends `keycloak`) adds the bundled Devanagari font.
  9. Postgres image: official `postgres:16.15-bookworm` + pinned PGDG PostGIS and pgvector
     packages (the postgis/postgis bullseye base is EOL).
  10. Staging deploy runs only after CI succeeds on `main`.
- **Deferred (tracked, not blocking M0):** pin GitHub Actions by SHA; per-key validation for
  `/admin/settings` and cross-process cache invalidation; split Compose networks and add a
  Valkey password; JWKS refresh throttling; caretaker logout endpoint; stronger import-linter
  contracts (only `service`/`deps`/`schemas` importable across modules, acyclic modules);
  paginated envelopes for list endpoints; `updated_at` on append-only tables (audit_log,
  outbox, jobs, login_links, invites) is intentionally omitted.
- **Operational note:** Keycloak imports the realm only on first start. Later realm-file changes
  must be applied in the admin console (or by re-creating the Keycloak database locally).

## 2026-09-30 — M0 foundation choices
- **Context:** Spec is silent or ambiguous on the points below; each is cheap to change later.
- **Decisions:**
  1. **Users table:** `phone` is nullable and `keycloak_sub` (unique) is added, because owners
     sign up in Keycloak with email and have no phone yet. `session_version` added so caretaker
     sessions can be revoked.
  2. **Caretaker sessions:** after a single-use link, the API issues its own HS256 session JWT
     (PyJWT, key `LINK_SIGNING_SECRET`, audience `farm-caretaker`, 30 days, setting
     `auth.caretaker_session_days`). Keycloak is not used for caretakers because they have no
     password and Keycloak has no magic-link flow. Revocation: bump `users.session_version`.
  3. **Login links:** random 256-bit tokens; only the SHA-256 hash is stored; single use via an
     atomic `UPDATE … RETURNING`; the token travels in the URL fragment so it never reaches
     server logs. Invites use the same scheme.
  4. **Roles:** `users.is_admin` / `is_agronomist` are the source of truth, set by admins via
     `/admin/users`; Keycloak realm roles are ignored. First admin via `python -m app.cli
     make-admin`.
  5. **Farm access:** non-members get 404 (existence not revealed), members without the role
     get 403 `FORBIDDEN_ROLE`. Admins and agronomists have no implicit farm access (spec 2).
  6. **Rate limits:** link requests 3 per 10 minutes per phone (spec) and 10 per 10 minutes per
     IP (decision), in setting `auth.link_rate_limit`.
  7. **Invite lifetime:** 7 days (`invites.ttl_days`). Invite acceptance and Telegram binding
     are built in M5; M0 returns a shareable link.
  8. **Extra tables:** `channel_accounts` (a user's chat id per channel) and `login_links`.
  9. **Config location:** process config is `app/config.py` (lowest import layer) rather than
     `app/core/config.py`, so adapters can read it without importing core.
  10. **Modules scaffolded now:** only `identity` and `farms`; later modules are created with
      `make new-module` in their milestone instead of empty shells.
  11. **Compose:** GlitchTip and Uptime Kuma are deferred to M8 (not needed for the M0
      definition of done). Extra compose secrets: `POSTGRES_PASSWORD`, `KEYCLOAK_DB_PASSWORD`,
      `FARM_RO_PASSWORD`, `KEYCLOAK_ADMIN_*`, `APP_BASE_URL`, `SITE_ADDRESS`.
  12. **Valkey client:** redis-py (MIT, Redis-protocol compatible) for the cache adapter and
      Celery broker.
  13. **pgvector:** built from the pinned `v0.8.6` tag on top of `postgis/postgis:16-3.5`,
      since no official image ships both.
  14. **Hindi font:** Noto Sans Devanagari (OFL) is bundled and self-hosted (~104 KB, two
      weights) so Hindi renders on every device and offline.
  15. **Frontend tooling:** Node 22 (Vitest 5 and jsdom need it), TypeScript 6.0 (typescript-eslint
      does not support 7 yet), react-router 7.
  16. **Keycloak:** Google login and SMTP are not in the realm import (they need real secrets);
      add them in the admin console. Keycloak has no Hindi translation, so Hindi texts for the
      login and registration pages are in the realm's `localizationTexts`.
- **Consequences:** recorded here so M5 (Telegram) and M7 (legal, data deletion) build on them.

## 2026-09-30 — Tooling: uv (Python) and pnpm (frontend)
- **Context:** Spec §4 names the libraries but not the package managers.
- **Decision:** `uv` for Python dependency/venv management, `pnpm` for the frontend. Makefile and hooks assume these.
- **Consequences:** Lockfiles `uv.lock` and `pnpm-lock.yaml` are committed; CI uses the same tools.

## 2026-09-30 — Telegram is the MVP channel; WhatsApp parts are post-MVP
- **Context:** Spec §2, §3 and §10 say "WhatsApp" in places, while §1, §4 and §12 say Telegram only in the MVP behind a `Channel` interface.
- **Decision:** Build Telegram only; keep WhatsApp names/tables reserved. Column values like `done_via = 'whatsapp'` are kept; a `telegram` value is added by an expand migration when M5 needs it.
- **Consequences:** `wa_sessions` and `/webhooks/whatsapp` are not built in the MVP.

## 2026-09-30 — Login: Keycloak + caretaker links, not phone OTP
- **Context:** §13's Login screen mentions phone OTP; §2/§4 say owners use Keycloak and caretakers use one-time messaging links, with no SMS cost.
- **Decision:** Follow §2/§4.
- **Consequences:** `/auth/otp/*` endpoints implement the caretaker single-use link flow despite their names.

## 2026-10-05 — Scope: 1 bigha and up; owner + caretaker or owner-farmer
- **Context:** Spec §1 says "terrace to about 2 acres". The first user is a land owner with 1 bigha or more, and the caretaker may be the owner.
- **Decision:** Target 1 bigha to a few acres. Terrace and kitchen gardens are out of scope. A farm may have no separate caretaker (the owner works it). Spec text is not edited; this entry and `docs/vision.md` override §1 on size.
- **Consequences:** Plots are large enough for satellite basemaps to be useful; plot templates T/S can be dropped later.

## 2026-10-05 — Plans follow the owner's goal; offer competing plans
- **Context:** The owner wants the land used to its potential according to their own goal (income, low labour, self-sufficiency).
- **Decision:** M3 should produce 2-3 candidate plans per goal with trade-offs; the owner picks. The goal is an engine input, not a label. Spec §7 to be checked when M3 starts.
- **Consequences:** Needs a goal vocabulary in settings/library, not hard-coded.

## 2026-10-05 — Government schemes are a product pillar
- **Context:** Subsidies, loans and rebates decide whether structures (drip, polyhouse, orchard, solar pump) pay back.
- **Decision:** Build the `schemes` table already in spec §17 with a status (`draft`/`ai_verified`/`approved`), a source URL and `last_verified`; match by plan and goal; wording "may be eligible"; subsidy only shown beside setup cost, never subtracted (§17). No in-app applications in the MVP.
- **Consequences:** A cited schemes seed (about 10-15 national and MP schemes) after the first crop batch; matching after M3; "apply by" tasks in M4.

## 2026-10-05 — `ai_verified` library status and AI research batches
- **Context:** No agronomist yet; M3 needs crop values. Decided earlier: AI drafts cited values, usable only behind a beta flag.
- **Decision:**
  1. New status `ai_verified` between `draft` and `in_review` (migration 0005, expand; status columns widened to 12 chars). Setting `library.allow_ai_verified` (default false) lets the engine use these entries (`service.engine_statuses`). Editing an `ai_verified` entry reopens it as a draft; agronomists can submit it for normal review.
  2. Each source may carry `quote` (the sentence that states the value) and `checked_on`. `scripts/check_research.py` opens every cited page and sets `checked_on` only when the quote is really on it. The fetch tool used during research rewords text, so only the script's check counts.
  3. `load-library` also loads `seeds/library/research/crops/*.json`: fills empty fields of drafts only; the crop becomes `ai_verified` when nothing is missing for review and every source is checked, otherwise it stays a draft with the gaps in `todo`.
  4. Value rules: ranges are stored at their lower bound (the full range is in the quote); `days_to_first_harvest` counts from bed planting (transplant date for nursery crops, matching spec §8); transplant sow windows are the source's nursery-sowing months shifted by the nursery days; windows that would cross 31 December are cut there; `water_need` is an interpretation of irrigation advice (flagged in the source note).
  5. `terrace_ok` is no longer required for review (terraces out of scope).
  6. Malwa sow windows use national ICAR-IIVR months until a Malwa-specific source is found.
- **Consequences:** Batch 1: tomato, brinjal, okra `ai_verified`; chilli and bottle gourd drafts (no source for the picking period). Sources: ICAR-IIVR, Kerala Agricultural University, NC State Extension.

## 2026-10-05 — Research batch 2
- **Result:** cucumber, radish, peas and bottle gourd (picking period added) are `ai_verified`; onion stays a draft (no national/Malwa source for seasons, sow windows and harvest timing; ICAR-DOGR to try); chilli still lacks a picking period.
- **Rules added:** TNAU Agritech pages are a source; picking periods may come from TNAU fertigation stage tables (noted on the value); a crop listed by NC State as "Full sun ... Partial Shade" is stored as `sun: partial`; cucumber sow windows are TNAU (Tamil Nadu) months because the ICAR-IIVR page was unavailable; the ICAR-IIVR pea yield line is mislabelled on the site and was not used.
- **Deferred to batch 3:** methi, coriander and spinach. Leafy crops are cut several times, so "first harvest" and "picking period" need a defined meaning first; seed-spice sources (ICAR-NRCSS) for methi and coriander. The `spinach` seed entry is *Spinacia oleracea*, but Indian palak is usually *Beta vulgaris* var. *bengalensis*; to settle before researching it.

## 2026-10-05 — Research batch 3 and the palak decision
- **Palak:** the library entry `spinach` is now Indian palak (*Beta vulgaris* var. *bengalensis*, "Palak (spinach beet)"), since that is what Indian farmers grow and what TNAU and ICAR-IIVR describe. Hindi name unchanged (पालक).
- **Result:** methi and coriander (leaf crops) are `ai_verified`. Palak is a draft with sourced timing, spacing and yield, but no source yet for sun, water need, height and waterlogging. Onion is a draft with only the Malwa sow windows missing (ICAR-DOGR's site could not be opened from this machine). Chilli still lacks a picking period.
- **Leafy crops:** the whole plant is pulled or cut, so `days_to_first_harvest` is the lower end of the source range and `harvest_span_days` the difference to the upper end (methi 20-25 days, coriander 30-40 days). Palak is cut repeatedly: first cut 30 days, then 60 more days (3 months total).
- **Onion:** maturity (110-120 days after transplanting, rabi in Madhya Pradesh) comes from an ICAR-DOGR variety release (Bhima Red), so it is one variety's figure.
- **Palak seasons:** from one ICAR-IIVR variety (Kashi Baramasi, Uttar Pradesh) described as suitable round the year.

## 2026-10-06 — M3 slice 1: layout engine (zones and beds, no crops yet)
- **Scope:** new `layout` module with `plans`, `zones`, `beds` (migration 0006), a pure engine (`engine.py`, version 0.1.0), `POST/GET /farms/{id}/plan`, and the plan drawn on the farm page. Template T (terrace) is not built (out of scope); S, M and L follow spec section 7.
- **Zone order and sizing:** border (inward band, mitred) -> north strip sized by binary search to its share of the parcel (+/-2%) -> pond at the lowest point when `slope_dir` is set, else far from the gate -> nursery next to the gate and utility next to the pond -> rotation field as a southern slab (L) -> beds are what is left. Pond, nursery, utility pieces are compact rectangles of aspect `layout.zone_aspect` pulled against the boundary. If the beds would get less than `layout.min_beds_share_pct` of their target, zones are dropped in the spec order (rotation, pond, orchard) with a warning.
- **Assumptions the spec does not give (settings, agronomist/owner to confirm):** `layout.gate_opening_m` 3 (gate gap left in the border, drawn as a "path" zone), `layout.nursery_share_of_utility` 0.5, `layout.zone_aspect` 1.5, `layout.min_beds_share_pct` 50, `layout.min_beds_axis_extent_m` 3 (spec 7).
- **Rules in draft are used by the engine** (they are the spec defaults); crops will still need `approved`, or `ai_verified` when `library.allow_ai_verified` is on.
- **Bed rules:** beds are tiled from the zone's west edge; B1, B2... are numbered from the gate side; trellis on every second column; raised beds when drainage is "waterlogs" or soil is black or clay; slivers under the minimum bed area or narrower than the minimum bed width are dropped.
- **Obstacles:** only the largest connected part of the plot is planned (warning if the plot is split).
- **Not verified yet:** golden and property tests (deferred by lean mode); checked on a 1-acre, 600 m2, rotated 2-acre, narrow strip and waterlogged test plot by running the engine and looking at one on the map.

## 2026-10-06 — M3 slice 2: crops per bed, layer and season (engine 0.2.0)
- **What:** `bed_layers` table (migration 0007), pure `planting.py`, plan API returns seasons and plantings, farm page shows "What grows when" by season, a reason per crop, and tapping a bed shows its whole year.
- **Spec 7 followed:** layers underground -> surface -> middle -> climber (climber only on trellis beds); hard rules: library status (approved, plus AI-checked while `library.allow_ai_verified` is on), sow window reachable, height <= `layout.tall_crop_cm` (2 m), waterlogging (raised beds exempt), no same family in a bed in consecutive seasons, no "avoid" pair in a bed; score value/diversity/ease/water with goal weights; greedy with slug tie-break; warning when fewer than `engine.min_crops` crops in a season.
- **Deviations / additions (spec silent or unworkable):**
  1. A layer stays busy until the crop's first harvest + picking period; the next crop in that layer is sown on or after that date (otherwise seasons overlapped).
  2. Eligibility follows each crop's own sow windows; season names (`engine.seasons` rule: kharif 1 Jun-15 Oct, rabi 16 Oct-28 Feb, zaid 1 Mar-31 May, a planning convention) only group plantings.
  3. Diversity is 1 for a crop's first use in a season, then 1 minus its share of that layer's beds. The spec's flat 0.3 for repeats let one crop take nearly every bed. `engine.score.repeat_diversity` is no longer used.
  4. With no local prices loaded, value = expected yield only (warning NO_PRICES).
  5. A "good" companion in the bed adds `layout.good_companion_bonus` (0.1) to the score.
- **Crop combinations data:** one pair so far, tomato + okra "good" (FAO AGRIS record of a two-summer field study in Peshawar), `ai_verified`. No "avoid" pairs: no checkable source found yet. More pairs need an agronomist or further research.
- **Data fix:** tomato height is now 1.5 m (TNAU staking advice) instead of NC State's whole-species range of 10 ft, which would have kept tomato out of beds. Research files now refresh untouched `ai_verified` entries on load.
- **Local stack:** `library.allow_ai_verified` set to true so the demo plans use AI-checked crops; plans then show "not yet reviewed by an expert".
- **Known limits:** every bed in a season is sown on the same first date (staggering is planner work, M4); a short leftover of a season at the plan start (e.g. "Kharif 2026", 5-15 Oct) shows as its own season; with 9 AI-checked crops every season is below the 6-crop target.

## 2026-10-06 — Visual plan: bed picture, year strip, machan guide
- **Why:** the plan was a wall of text; multilayer farming needs to be seen. The farm page now shows season tabs above the map, beds coloured by their main crop (tap a crop chip to light up its beds, others dim), and a tapped bed opens a side-view drawing (machan, climber, main crop, leafy layer, roots; raised bed shown raised) with the same layers listed top to bottom, plus a year strip (sowing light, harvest solid).
- **Harvest dates:** `bed_layers.harvest_start/harvest_end` (migration 0008) = sowing + days to first harvest + picking period, from the library.
- **Machan (trellis) guide:** stored as library rule `guide.machan` (five steps, each with a TNAU or KAU quote; Hindi is a translation; status draft until an agronomist reviews). Shown on the farm page when the plan has a climber. The drawing uses the `engine.bed` trellis height (2.1 m, spec default); TNAU says 2 m for gourd pandals and KAU says 1.5 m is common in Kerala, so the height is a config value. Post spacing and rope pattern are not in the sources, so the guide says to ask a local builder or the KVK.
- **Crop colours and emoji** are presentation only (`frontend/src/plan/cropStyle.ts`); no agronomy. Emoji need a phone's emoji font.
- **Drawing is schematic:** layer heights in the picture are not to scale; only the labelled dimensions (frame height, bed width, path width) come from rules.

## 2026-10-06 — Plan options (goal-driven) and owner editing
- **Five options built side by side** for every farm (vision: the goal drives competing plans): Most income, Balanced, Low work/low risk, Family food and soil, Water saver. Each is a full engine run (zones, beds, crops) with its own zone-share changes and score weights from the library rule `engine.options` (product defaults, draft, agronomist to review). Zone changes stay within the spec's +/-10 points; each option also changes its beds target, so optional zones are not dropped in a way that reverses the option's intent (e.g. Low work ending with more beds).
- **Goal match:** the option whose `for.goal` matches the farm's goal is "Best for your goal"; options matching who works the farm (caretaker) or the water source (rain only) say so. Options replace the spec's goal weight shift (income -> value 0.55, home food -> diversity 0.45), which now only applies to a plan built without an option.
- **Comparison figures** per option: beds, bed area, crops, estimated harvest (kg/year), a water index (bed area x water need x days in the ground) and a work index (bed area x days under crops), shown as low/medium/high against the middle option (+/-15%). Money is not shown yet (no cost or price data).
- **Owner editing:** "Use this plan" makes a plan active (one per farm, the previous one archived). "Change this plan" re-runs the option with land-use changes in 5-point steps (max 10 per use) and a bed size (`layout.bed_widths`: narrow 0.9 m = minimum bed width, standard 1.2 m = spec, wide 1.5 m = product default, agronomist to confirm) as a new draft marked "Your changes". "Change" on a bed layer lists only crops that pass every engine rule there (season window, layer free in time, ends before the next crop, rotation, height, waterlogging, avoid pairs); the owner's pick is stored with reason "Your choice".
- **API:** `POST/GET /farms/{id}/plan/options`, `GET /farms/{id}/plan?plan_id=`, `POST .../plan/{plan_id}/adjust`, `POST .../plan/{plan_id}/lock`, `GET .../beds/{code}/alternatives`, `PUT .../beds/{code}/layers`. Migration 0009 adds `plans.option` and `plans.batch`.
- **Known limits:** with 9 crops the options differ mostly in land use; crop choice differs little until more crops (and low-care flags, prices, water needs) are in the library.

## 2026-10-06 — Government schemes and benefits (vision pillar 6)
- **Data:** `schemes` table in the site module (spec 17, extended per the vision: level, state, benefit type, what it gives, eligibility, documents, where to apply, structured `rule`, cited `sources`, `checked_on`, status). Seed `seeds/site/schemes.json` (12 schemes) is loaded by `load-site-data`; every statement quotes an official page and `scripts/check_research.py` confirmed all 23 quotes, so all 12 are `ai_verified`.
- **Schemes (first batch):** PM-KISAN, Kisan Credit Card interest support (MISS), PMFBY crop insurance, PMKSY Per Drop More Crop, PM-KUSUM solar pump (Component B), MIDH new fruit garden, MIDH farm pond, MIDH polyhouse/net house, Agriculture Infrastructure Fund, National Mission on Natural Farming, MP fruit area expansion, MP protected cultivation.
- **Sources:** pmindia.gov.in cabinet decisions, MNRE, the PMKSY portal, district/state government pages (Pune, Hojai, Telangana State Horticulture Mission for MIDH norms, Nagaland horticulture, Uttarakhand agriculture), MP horticulture department and MPFSTS. PIB and most guideline documents are PDFs or JavaScript-only pages the checker cannot read; where a figure was only in those (e.g. the micro-irrigation 55%/45% split, MP state scheme amounts) the entry says to check the MPFSTS portal instead of stating a number.
- **Matching:** structured rules only (no LLM): plan tags (beds, orchard, pond, utility, rotation, nursery, `goal:*`, `option:*`) and farm facts (electricity, water source). Unknown facts do not hide a scheme; they become "check first" items. State schemes are shown when the state matches `site.default_state`. Each card says why it is shown.
- **Wording:** always "may be eligible"; the card ends with "confirm with the district agriculture or horticulture office before buying anything". Documents are listed only when a source states them; otherwise "ask at the office". Subsidies are not subtracted from any cost (spec 17; costs are not built yet).
- **Not yet:** "apply by" tasks in the weekly plan (M4), more state/district schemes, agronomist/expert review, a refresh routine for changing amounts.

## 2026-10-06 — Goal step (setup step 3 of 3)
- **Why:** the vision makes the goal the main input; setup used a silent default ("both").
- **What:** after the plot is saved the first time, setup asks: main goal (Earn the most / Steady income, little work / Food for my family and healthy soil / A mix), farming methods wanted (multilayer, fruit orchard, flowers, natural farming, polyhouse/shade net, integrated; multilayer, orchard and natural are preselected), setup budget band (under ₹1 lakh / ₹1-5 lakh / over ₹5 lakh: product defaults, not data) and who works. "Decide later" keeps sensible defaults. Saving builds the five plan options right away. The farm page links back to it ("Change goal and farming methods").
- **Data:** farm goal gains `low_work`; new `farms.methods` (array) and `farms.budget_band` (migration 0011).
- **Use:** `engine.options` now maps goal, who works, water and methods to options (e.g. steady income -> Low work; polyhouse interest -> Most income; natural/integrated -> Family food and soil). Methods also drive what gets planted (flowers, orchard) and which extra zones are offered (polyhouse, integrated) in the next slices.

## 2026-10-06 — Research batch 4: fruit trees, border plants, flowers
- **AI-checked:** guava, lemon (acid lime), pomegranate, jamun, custard apple, banana; curry leaf (border); marigold and chrysanthemum (flowers). Drafts: mango and amla (no checkable source for years to first fruit). New library entries (shells): chrysanthemum, tuberose, gladiolus, rose.
- **Sources:** TNAU fruit and flower pages, Kerala Agricultural University fruit pages, the National Horticulture Board pomegranate project report, an ICAR journal abstract (custard apple, one early variety), NC State Extension.
- **Requirement change:** what must be filled before review is now what the engine uses: always family, seasons and water need; bed crops add harvest timing, spacing, yield and waterlogging; trees (fruit trees, papaya, banana) add tree spacing and years to first fruit; border plants add spacing. Sun, height and canopy are optional (trees go in the open north strip; spacing drives the layout).
- **Value rules:** tree yields per hectare or per tree are stored per m² of orchard (per tree / spacing²); watering every 7-10 days or less is read as "low" water need, every few days as "medium" (flagged as interpretation); custard apple's 2 years is one early variety (noted).

## 2026-10-06 — Trees, hedge and flowers in the plan (slice C)
- **Orchard strip:** trees are placed in east-west rows, one species per row at its own library spacing, widest spacing furthest north (less shade on the rest); rows repeat until the strip is full. Species are ranked per plan option (yield, years to first fruit, water need, using the option's weights) and each option uses a set number of species (`engine.options.tree_species`: income 2, balanced 3, low work 3, family food 4, water saver 2). Planting date = first planting-window day in the plan year (plan start if the source gives none); first fruit = planting + years to first fruit.
- **Border:** the best-ranked border plant (so far curry leaf) is spaced along the middle of the border band at its library spacing, leaving the gate open.
- **Flowers:** marigold and chrysanthemum go in beds (middle layer) only when the owner picked "Flowers" in the goal step.
- **Storage:** `zone_plants` (one row per tree or hedge plant; migration 0012). The plan returns them grouped per crop with planting date, first fruit and a yearly harvest once bearing (library yield per m² x spacing² per tree; an estimate).
- **Not yet:** intercrops between young trees (TNAU advises pulses and short vegetables before trees bear; shown as advice, not planned), mango and amla (missing years to first fruit), more border plants.

## 2026-10-06 — Methods made visible; polyhouse and integrated zones (slices D and E; engine 0.3.0)
- **Scope change:** spec 1 and 16 list polyhouse and livestock as post-MVP/future templates. The vision (owner's goal and methods) brings them in now in a minimal form: a zone in the layout, not yet animal numbers, polyhouse crop calendars or structure costs.
- **Polyhouse:** when the owner picks "Polyhouse" in the goal step, a polyhouse zone (`layout.extra_zones.polyhouse`, 8% of the plot, product default) is carved next to the compost and tools area and tiled with covered beds (`beds.protected`, migration 0013). Covered beds use the same crop rules and sowing windows as open beds until a cited source for protected-cultivation calendars is added. The MIDH and MP protected-cultivation schemes now match a plan with a polyhouse.
- **Integrated farming:** when picked, a livestock area (`layout.extra_zones.livestock`, 5%) is carved next to the compost area (manure -> compost -> beds). Which animals and how many is not planned yet (no cited livestock data).
- **Room:** zones the owner asked for are taken out of the beds target, so they are not the first thing dropped; if the plot is still too small they are dropped first, with a warning and a note in "How this plan farms".
- **"How this plan farms":** the farm page lists only the methods the plan really uses, each in one plain sentence: multilayer beds (beds with 3-4 crops at once), fruit orchard, polyhouse, integrated, the water and compost loop, natural farming (states that recipes such as jeevamrut are not in the library yet), living fence, crop rotation.

## 2026-10-06 — Research batch 5: more vegetables
- **AI-checked:** bitter gourd, ridge gourd, carrot, french (bush) beans. **Drafts:** cabbage (no drainage statement in the source), cauliflower (no first-harvest day), beetroot and cluster bean not written (no harvest window; the cluster bean yield line is garbled on the page). 22 crops are now AI-checked in total.
- **Rules:** first picking for gourds and cabbage = TNAU fertigation "total duration" minus its "harvesting stage" (noted on the value); a weekly watering is read as "low" water need, every few days as "medium" (interpretation, flagged). Sow windows are TNAU plains months.
- **Still missing:** soil builders (dhaincha, sunn hemp) and pulses (no readable TNAU/KAU page found in this round), lemongrass, vetiver and karonda water needs, mango and amla years to first fruit, onion Malwa windows, chilli picking period.
- 2026-10-07 Research batch 6: capsicum, beetroot, amaranth, cluster bean and drumstick are `ai_verified`; amla (years to bear 3, NHB) and mango (6, NHB; grafts may bear earlier) now complete. Drumstick moved from vegetable to fruit_tree so it is planned as an orchard tree (spacing 2 m). `chaulai` is the same plant as amaranth, so it stays a name only (draft, no research) to stop the planner planting it twice. Pulses, cereals, millets, oilseeds and green manures were not researched: the engine plans only beds, trees, hedge and flowers, so they would change no plan until the rotation field is planted. Crops still blocked on a missing value: cabbage (drainage), cauliflower (picking period), chilli (picking period), onion (Malwa sow dates), spinach (water, drainage), papaya (years to bear), sweet potato (drainage), colocasia and turmeric/ginger (picking period). `scripts/check_research.py` now retries dropped connections (the TNAU server drops some).
- 2026-10-07 Data scope (owner): use all-India crop data, focus on Madhya Pradesh for the MVP. Regions are now `malwa` (the farm's region), `madhya-pradesh` and `india`; `library.region_fallback` (setting) is the lookup order for a crop's sowing window after the farm's own region. All windows stored so far came from Tamil Nadu pages, so they moved from `malwa` to `india` (migration 0014); `malwa` now means Malwa data only. A crop needs a sourced window in any region of the chain. `scripts/check_research.py` reads PDFs too (dev dependency `pypdf`, BSD, pure Python), because most state and ICAR guides are PDFs; Vikaspedia pages need JavaScript and cannot be checked by script.
- 2026-10-07 Research batches 7-8: field crops (moong, urad, chana, soybean) take their sowing months from the Madhya Pradesh crop-season table (SLBC, a PDF) under region `madhya-pradesh`; growing facts from TNAU. New crops added to the library: sapota, litchi, orange (mandarin), potato, snake gourd, jackfruit, watermelon. Garlic, ginger, turmeric, potato, snake gourd, papaya, watermelon use the Kerala Agricultural University crop pages (celkau.in, plain text, one topic per page), which give the picking period and drainage most other pages omit. Derived values (a span from a range such as 90-130 days) are explained in each source note. Tree yield per m2 is derived from yield per tree and spacing where the page gives per-tree figures.
- 2026-10-07 Research batches 9-10: PAU Ludhiana's vegetable package (a PDF; north India, so rabi vegetables match Malwa winters better than Kerala pages) completes spinach (water, drainage), cauliflower (picking period), sweet potato, colocasia and broccoli; lemongrass from TNAU aromatic crops. Engine 0.3.1: new rule `engine.orchard` (max 1 quick-fruiting species, i.e. years to bear <= 1, in the orchard) because papaya, drumstick and banana out-yield long-lived trees per m2 and had filled the orchard; product default, agronomist to confirm.
- 2026-10-07 Research batches 11-14 (TNAU and PAU crop-production PDFs, now read by the source check): chilli picking period; sem, mint, tinda, cowpea; kutki and kodo millet (TNAU calls them samai and varagu); wheat, mustard, maize, bajra, arhar, sesame, groundnut, linseed (Madhya Pradesh sowing months from the SLBC table); dhaincha and sunn hemp; rose as a flowering hedge (category border); dragon fruit. Workflow change (spec silent): drilled field crops need no per-plant spacing (`CROP_FIELD` = days, row spacing, yield) and green manures need only days until dug in and row spacing (`CROP_GREEN_MANURE`), because plant count is not planned for them. Whole-centimetre spacing only: sunn hemp's 22.5 cm is stored as 23.
- 2026-10-07 Library gaps after batch 14, all still names only: bamboo, karonda, vetiver (no water need or years to bear), gladiolus and tuberose (yield only as flower counts; no days to first flower for tuberose), dill (grown as a seed spice in the PAU guide, no leaf harvest), lettuce, knol-khol, mustard greens, pole beans, ivy gourd, pointed gourd, sponge gourd (no picking period, drainage or sowing months in any source found). Chaulai stays a duplicate name of amaranth.
- 2026-10-07 Crop combinations: 77 crop pairs (65 good, 12 avoid), every one with a quote from PAU, TNAU, KAU, NHB, ICAR or FAO that the check confirmed. Good pairs are recommended intercrops (PAU/TNAU/KAU), natural-farming vegetable combinations (ICAR, Himachal) and trap crops; avoid pairs are PAU's explicit "should not be grown" lists for mango and Kinnow orchards (maize, bajra, okra, vine vegetables). Pairs apply to crops grown in the same bed in the same season; 18 of them involve trees and are for the future "intercrops under young trees" feature, so plans do not use them yet. Hindi reasons are mine and need a native review. No source gave an avoid pair between two bed crops, and shared-pest "avoid" pairs were not invented: tomato and okra are both Helicoverpa hosts yet grow well together. "Do not grow X after Y" statements (brinjal after pea, turmeric after banana) are sequence rules, not pairs; the relation has only good/avoid, so they are not stored (would need a new relation type). `scripts/check_research.py` now detects PDFs by content because ICAR download links have no .pdf ending.
- 2026-10-07 Recipes: all 10 are `ai_verified` with ingredients, quantities, steps, timings and a quote for each. Seven (beejamrit, jeevamrit, ghanjeevamrit, neemastra, brahmastra, agniastra, dashaparni ark) come from NITI Aayog's Natural Farming Training Toolkit; panchagavya and vermicompost from TNAU; sour buttermilk from PAU (wheat yellow rust) plus NITI. `per_area_sqm` means the area one batch treats: 200 litres of jeevamrit or neemastra = one acre; for brahmastra, agniastra, dashaparni ark and ghanjeevamrit it is derived from the batch size and the stated dose and flagged in the source note (dashaparni ark: one 210-litre batch covers about 26 acres); panchagavya from 50 litres/ha through irrigation. Rule change (spec silent): a seed-treatment recipe (beejamrit) needs no per-area figure because its batch is sized by seed weight (20 litres treat 100 kg). Safety notes are NOT sourced yet for any recipe, including those with tobacco, chilli and datura; the source texts have none. Each recipe carries a TODO for the agronomist, and recipes should not be shown to farmers without safety notes. Hindi steps are mine and need a native review. New loader `load_recipe_research` reads seeds/library/research/recipes/*.json.
- 2026-10-07 Pests and diseases: 31 entries (19 pests, 11 diseases and root-knot nematode), all `ai_verified`, each with symptoms and a quote. Symptoms and cultural management come from TNAU's crop-protection pages (one page per pest or disease); the recipe link comes from NITI's natural-farming toolkit, matched to the pest class (sucking pests: neemastra; borers and fruit fly: agniastra; jassids and nematodes: brahmastra; fungal and viral problems: sour buttermilk). Schema change (expand, migration 0015): `pests.management_en` and `management_hi`, because traps, trap crops and cultural steps are the main non-chemical control and the spec's columns had no place for them; the chemical sprays in the sources are deliberately left out. `months` only where a source gives one (mango hopper: February); `escalate_if` is empty everywhere because no source gives an escalation rule, so each pest carries a TODO for the agronomist. Crops covered: tomato, brinjal, chilli, okra, potato, onion, mango, guava, sapota, drumstick and banana; none yet for cabbage and cauliflower, cucurbits, pulses, field crops, citrus, banana diseases or papaya. Hindi is mine and needs review.
- 2026-10-07 Water and height data (migration 0016 adds `crops.kc`): crop coefficients (Kc ini, mid, end) for 34 crops from FAO Irrigation and Drainage Paper 56, Table 12; Kc ini is the group value where the table gives one per group, ranges are stored at their lower end. Litres of water per day are not stored for beds because they need the farm's reference evapotranspiration (ET0), which the site profile does not hold yet (no sourced Indore ET0 table was found); the water check will compute litres = Kc x ET0 per farm once the site profile gets ET0. For 7 trees (mango, banana, orange, guava, sapota, amla, papaya) `water_l_per_sqm_day` is derived from TNAU's litres per tree per day over the library spacing (mature, and young at one third). `height_max_cm` for 24 more crops from FAO's mean maximum plant height. Prices are still blocked: the mandi price feed needs a DATA_GOV_IN_API_KEY from the owner, and no price was invented or taken from a shared demo key.
- 2026-10-07 Pests batch 2 (migration none): 54 pests and diseases in all. Added cabbage-family pests (diamondback moth, cabbage butterfly, cabbage aphid), cucurbit fruit fly and red pumpkin beetle, citrus pests and diseases (leaf miner, psylla, aphid, gummosis, canker, greening), pulse pests (gram and spotted pod borers, bean aphid, pod fly, pod bugs), yellow mosaic of moong and urad, chickpea wilt, dry root rot and Ascochyta blight, and mustard aphid, sawfly and painted bug. First `escalate_if` values: only where the page gives an economic threshold (spotted pod borer: 5 larvae per plant; bean aphid: 20 per 2.5 cm of shoot). Still no pest pages found for banana, papaya, guava diseases, cucurbit diseases, cauliflower diseases or wheat and maize pests.
- 2026-10-07 Root depth: `root_depth_cm` for 34 crops from FAO-56 Table 22 (lower end of the range, which the page says suits irrigation scheduling). The table's depletion fraction (p) is not stored: no column yet.
- 2026-10-07 Cost norms (migration 0017, site module): 18 setup-cost lines with the government's subsidy rate, from the MIDH Operational Guidelines 2025 (NHB, dated 31 Dec 2024), each with a quote the check confirmed: polyhouse (naturally ventilated, fan and pad, bamboo), shade net, low tunnel, vegetable and flower cultivation in a polyhouse, mulching, vermicompost unit and vermibed, new orchards (regular and high density, minor fruits, banana) and GAP certification. Money is integer paise per unit (sqm, ha or unit) with size tiers; the subsidy is the general-area rate (40% for orchards, 50% for structures), north-eastern and Himalayan states get more. `GET /api/v1/cost-norms` lists them for any signed-in user. Still missing for a full setup-cost estimate: drip irrigation and farm ponds (the guideline says only 'as per PDMC norms', so they need the PM-KSY micro-irrigation norms), fencing, and local retail prices for seed, compost and mulch; the estimate itself is not built.
- 2026-10-07 KVK directory (migration 0018, site module): 44 Krishi Vigyan Kendras of Madhya Pradesh with district, address, phone and email, each row with the quote it came from (TNAU Agritech list for Zonal Coordinating Unit VII); all 44 quotes confirmed by the check. The list is undated, so each source note says to confirm the phone number; no Hindi names yet (needs native review). The district is stored as the source lists it (Hoshangabad, not Narmadapuram; Barwani, not Badwani). `GET /api/v1/kvks?district=` for signed-in users; nothing uses it in the UI yet. The ICAR list (54 KVKs, host organisation and year) was not merged because it names villages, not the same address strings.
