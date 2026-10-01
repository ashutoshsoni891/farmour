## 11. AI helper

The AI helper explains, answers and triages; it never decides layouts, never writes to plans or the library, and says "not sure" rather than guessing.

### Uses in the MVP

1. **Plan explanation:** after the engine runs, a plain-language summary of why each zone and crop was chosen (from `plans.summary` + rule codes), in the owner's language.
2. **Q&A** from the web app and WhatsApp, grounded in the library and this farm's data.
3. **Photo check:** a plant photo in → likely issue, confidence, organic remedy from `recipes`, and whether to call an expert.
4. **Free-text parsing** for WhatsApp logs (section 10).

### Agent design (LangGraph)

Nodes: `classify_intent` → `retrieve` → `call_tools` (loop, max 4 calls) → `compose_answer` → `safety_check` → respond.

Read-only tools, all scoped to the caller's `farm_id` and role:

| Tool | Returns |
| --- | --- |
| `get_farm_summary()` | Area, template, zones, current season |
| `get_bed(code)` | Bed size, current plantings, recent logs |
| `get_tasks(range)` | Pending and overdue tasks |
| `get_weather()` | Latest 7-day snapshot and active alerts |
| `search_library(query, lang)` | Top 6 approved chunks with source IDs |
| `get_recipe(slug)` | Ingredients, quantities for the bed area, steps |
| `get_profit(period)` | Owner only; blocked for caretakers without money access |

### Retrieval

- Chunk approved library entries per crop, pest and recipe (about 300–500 tokens), one chunk per language; embed and store in `library_chunks`.
- Hybrid search: vector similarity + Postgres full-text on crop names (Hindi and English synonyms, e.g. lauki / bottle gourd / लौकी).
- Answers must cite chunk IDs internally (`ai_messages.citations`); the UI shows "Based on: Bottle gourd guide".

### Photo check (post-MVP)

- Resize to max 1,568 px, strip location metadata, send to the vision model with the bed's crop, season and recent weather.
- The model returns strict JSON: `{"issue_slug" | null, "confidence": 0–1, "observations": [], "recipe_slugs": [], "escalate": bool}`; only slugs that exist in `pests` / `recipes` are accepted.
- Confidence ≥ 0.7 → show the issue and remedy and add an `apply_recipe` task (owner can undo). 0.4–0.7 → "possibly X", suggest a closer photo. < 0.4 or `escalate` → "not sure; show this to an expert", with KVK contact from settings.

### Guardrails

- System prompt: answer only about this farm and the approved library; if the library lacks the answer, say so and suggest asking an expert. Never recommend chemical pesticides; never give dosages not in a recipe.
- `safety_check` node rejects answers that mention crops, quantities or recipes absent from the retrieved context, then retries once with a stricter instruction or returns the fallback "I don't have verified information on this yet."
- Human health, animal health, legal and financial questions get a polite redirect.
- Limits: `max_ai_messages_per_day` per user (default 30), token logging per message, prompt caching for the system prompt and library context.
- Prompts are versioned files; every `ai_messages` row stores the prompt version and model name.
- Agronomist review queue: any answer a user marks "wrong" plus a 5% random sample go to the agronomist weekly.

