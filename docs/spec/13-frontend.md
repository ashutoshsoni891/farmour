## 13. Frontend

One responsive PWA serves owners on laptop and phone and caretakers who prefer an app; it must work on a mid-range Android phone over 3G.

### Screens

| Screen | Key elements |
| --- | --- |
| Login | Phone number, OTP (auto-read on Android), language switch visible before login |
| Farm setup wizard | 1. Site type (ground / terrace) → 2. Draw boundary on satellite map, or enter side lengths for a rectangle, or upload KML → 3. Mark gate and obstacles → 4. Soil, drainage, slope (pictures for each option, "not sure" allowed) → 5. Water source and summer availability → 6. Goal, budget, labour → review. Progress saved after every step. |
| Plan view | Scaled map of zones and beds (colour by zone kind, pattern for trellis beds), north arrow, scale bar; tap a bed → layers per season; side panel: summary, costs, warnings, AI explanation |
| Plan editor | Zone share sliders (±10 points), swap crop in a layer (only valid candidates listed), rename beds; "Regenerate" shows a diff before saving |
| This week | Tasks grouped by day and bed; one-tap done; overdue on top; filter by bed |
| Log | Big buttons: Harvest / Cost / Sale / Photo / Note; bed picker; number pad; works offline |
| Money | Period switcher; revenue, costs, profit; per-zone cards; plan-vs-actual per planting (green / amber / red); payback estimate |
| Ask | Chat with the AI helper; photo button; sources shown under answers |
| Team | Invite caretaker by phone, toggle money visibility, see message delivery status |
| Library (agronomist) | Table of crops with status; edit form with validation; approve button; review queue of flagged AI answers |

**Setup wizard in the MVP (shorter):** 1. Site type → 2. Pin location and draw or enter the boundary → 3. Mark gate and obstacles → 4. **"We found for your land" card** from site intelligence, where the owner confirms or changes each fact; soil, drainage and slope questions appear only when confidence is low or the owner taps Change → 5. Water source and summer availability → 6. Goal, budget, who works → review. **Also add a Shopping list screen:** season switcher, items with quantity, rough cost, nearest source, and a "bought" tick.

### Map and drawing details

- MapLibre GL with a satellite base layer (check the tile provider's licence and usage limits); Terra Draw for polygons with vertex editing and snapping.
- Show live area in the user's unit while drawing; warn when self-intersecting.
- Offer "enter measurements" for users who can't use a map: rectangle (length × width) or four sides + one diagonal.
- Bijalpur-style small plots: allow zoom to 0.5 m precision; show a 1 m grid.

### Offline behaviour

- Service worker caches the app shell, active plan, next 14 days of tasks and bed list.
- Logs and task updates made offline go to an IndexedDB queue with `client_uuid`; sync on reconnect via `/logs/batch`; show a "3 items waiting to sync" badge.
- Photos queue locally, compressed to max 1,600 px and about 300 KB before upload.
- Conflict rule: server wins for plans; for tasks, the latest `done_at` wins.

### Language, units and accessibility

- Hindi and English complete from day one; every string is an i18n key; crop names come from the library in both languages.
- Units follow `unit_pref`; bigha shows only if the user has set `bigha_sqft` (bigha size differs by region).
- Minimum 16 px text, 44 px touch targets, icons with labels, high contrast (outdoor use in sunlight).
- Numbers in Indian format (1,00,000); dates as "28 Sep" / "28 सितंबर".

