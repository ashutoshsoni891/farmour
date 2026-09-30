---
paths:
  - "frontend/**"
---

# Frontend rules (spec §13)

- React 18 + TypeScript `strict`, Vite, TanStack Query, Tailwind. API client is generated from OpenAPI; do not hand-write fetch types.
- PWA via Workbox; offline writes go to a Dexie (IndexedDB) queue with `client_uuid`, synced via `/logs/batch`; show "N items waiting to sync". Server wins for plans; latest `done_at` wins for tasks.
- i18n: every user-facing string is an i18next key in `i18n/en.json` and `i18n/hi.json`; no literals in JSX. Crop names come from the library in both languages.
- Accessibility for outdoor mobile use: min 16px text, 44px touch targets, labelled icons, high contrast.
- Indian number format (1,00,000); dates "28 Sep" / "28 सितंबर"; units follow `unit_pref` (bigha only if `bigha_sqft` set).
- Must work on a mid-range Android phone over 3G (first load < 5 s). Check at mobile width in Hindi and English.
- Never show sale/profit figures to a caretaker without money access (UI is not the only guard; the API enforces it too).
