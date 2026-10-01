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

