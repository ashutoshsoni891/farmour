## 3. System architecture

The MVP is a modular monolith: one FastAPI backend with clear internal modules, one Postgres database, S3-compatible object storage for files, and four external services, all self-hosted with Docker Compose. Split modules into separate services only when load demands it.

&#91;embedded content: Lean MVP architecture · 9 modules incl. site intelligence · open-source, self-hosted · no IoT\]

### Module responsibilities

| Module | Owns | Reads from | Never does |
| --- | --- | --- | --- |
| Parcel and layout | `parcels`, `zones`, `beds`, `bed_layers` | Crop library, settings | Call the LLM to decide geometry |
| Crop library | `crops`, `crop_varieties`, `companions`, `recipes`, `pests`, `rules` | — | Publish entries not approved by an agronomist |
| Planner and tasks | `plans`, `plantings`, `tasks` | Layout, library, weather | Delete completed tasks |
| Records and profit | `logs`, `sales`, `costs`, profit views | Plantings, tasks | Show money to caretakers without permission |
| AI helper | `ai_conversations`, `ai_messages`, `photo_checks` | Library (pgvector), farm data (read-only tools) | Write to plans or library |
| Weather alerts | `weather_snapshots`, `alerts` | Open-Meteo | Send more than 1 alert per farm per day unless severe |
| Messaging | `messages`, `message_templates`, `wa_sessions` | Tasks, alerts | Send free-form WhatsApp outside the 24-hour window |
| Plan export | `exports` | Layout, plan | Expose private farms without a signed link |
| Scheduler | `jobs` | All modules | Run a job twice for the same key (idempotency) |

**MVP module changes:** add **Site intelligence** (owns `site_facts`, `mandis`, `mandi_prices`, `places`, `schemes`, `geo_cache`; section 17). The shopping list is part of the planner module. Weather alerts, photo check and plan export are post-MVP; their rows above describe the future design.

### Walkthrough: from drawing a plot to a caretaker's WhatsApp

1. Owner draws the parcel on the map; the API stores it as a PostGIS polygon and computes area and orientation.
2. Owner picks goal, budget and start date; the layout module generates zones, beds and layers using library rules (section 7).
3. Owner accepts the plan; the planner creates plantings and a dated task list (section 8).
4. Every Sunday 18:00 IST the scheduler sends each caretaker their week's tasks on WhatsApp; each day at 07:00 IST it sends that day's tasks.
5. Caretaker replies "done" / "not done" or sends a photo or harvest amount; messaging parses it and writes a log.
6. Weather job runs at 05:30 IST; if a threshold is crossed it shifts affected tasks and alerts owner and caretaker.
7. Owner sees plan-vs-actual and profit on the dashboard.

