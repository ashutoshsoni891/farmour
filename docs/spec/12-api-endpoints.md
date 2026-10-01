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

