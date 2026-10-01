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

