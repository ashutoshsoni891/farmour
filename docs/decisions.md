# Decisions

Record every structural choice: context, decision, consequences. Newest first. Template:

## YYYY-MM-DD — Title
- **Context:**
- **Decision:**
- **Consequences:**

---

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
