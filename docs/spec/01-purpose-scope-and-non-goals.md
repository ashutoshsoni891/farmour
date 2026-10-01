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

