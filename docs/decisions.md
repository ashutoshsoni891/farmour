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
