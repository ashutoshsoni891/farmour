# Decisions

Record every structural choice: context, decision, consequences. Newest first. Template:

## YYYY-MM-DD — Title
- **Context:**
- **Decision:**
- **Consequences:**

---

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
