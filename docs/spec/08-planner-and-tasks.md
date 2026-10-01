## 8. Planner and tasks

When the owner activates a plan, the planner creates one planting per bed-layer-season and a dated task list for the next 12 months; it regenerates the next 8 weeks nightly so changes flow in.

### Planting dates

- `planned_sow` = the first date ≥ plan start inside the crop's sow window; if `nursery_days` is set, a nursery sowing task comes `nursery_days` earlier and the bed task becomes "transplant".
- `planned_harvest_start` = sow + `days_to_first_harvest`; `planned_harvest_end` = start + `harvest_span_days`.
- Stagger leafy crops: split a leafy layer into 2–3 sowings 14 days apart (setting) so harvest is continuous.

### Task types

| Type | Generated when | Default window | Notes |
| --- | --- | --- | --- |
| `prepare_bed` | 7 days before first sowing in a bed | 5 days | Includes compost quantity: 3 kg/sqm default (setting) |
| `nursery_sow` | sow date − `nursery_days` | 2 days | Tray count from plant count + 20% |
| `sow` / `transplant` | planned sow date | 3 days | Quantity and spacing in params |
| `mulch` | 3 days after sowing | 3 days |  |
| `install_trellis` | 10 days after climber sowing | 5 days | Only beds with `has_trellis` |
| `apply_recipe` | every `apply_every_days` per recipe (e.g. jeevamrut 15 days) | 2 days | Linked prep task (`prepare_recipe`) created `ferment_days` earlier |
| `pest_check` | weekly per active bed | 2 days | Asks for a photo if anything looks wrong |
| `harvest` | weekly from harvest start to end | 2 days | Reply collects kg |
| `clear_bed` | day after harvest end | 3 days | Triggers next season's `prepare_bed` |
| `weather_action` | from alerts (section 9) | 1 day | E.g. "cover greens with shade net" |
| `manual` | owner creates | owner sets |  |

Watering is not a daily task (it would spam users); it appears as a standing instruction in the weekly digest, with litres per bed from the engine. A weekly `water_check` task asks "is drip reaching all beds?".

### Batching and status

- Tasks are sent in two batches: a weekly digest (Sunday 18:00 IST) and a daily list (07:00 IST) of tasks whose window starts that day. Max 8 tasks per daily message; the rest are summarised with a link.
- A task not done by `due_date + window_days` becomes `overdue`; owners get one overdue summary per day, never per task.
- `idempotency_key` = `farm_id:type:planting_id:due_date`; regeneration upserts on it and never duplicates or revives cancelled tasks.

### Rescheduling rules

- **Missed sowing:** if still inside the sow window, move to the next day and re-send; if the window has closed, mark the planting `skipped` and propose the best alternative crop for that layer from the engine (owner approves in one tap).
- **Crop failure** (caretaker reports "failed" or photo check says severe): planting → `failed` with reason; offer a replacement if a sow window is open within 21 days.
- **Early or late harvest reported:** shift that planting's later harvest tasks and `clear_bed` accordingly.
- **Weather:** heavy rain forecast moves `sow`, `apply_recipe` and `mulch` tasks out of the rain days; heat alerts add shade tasks.
- Every reschedule writes an `audit_log` entry with the reason, shown to the owner as "Changed because...".

The weather rescheduling rule above is post-MVP (it depends on forecast alerts).

### Shopping list (MVP)

- Generated per season from the plan's plantings and due recipes, and regenerated whenever the plan changes.
- Items: seeds or seedlings (plant count + 20% buffer), saplings, compost (kg by bed area), mulch, recipe ingredients (jaggery, besan, neem), and drip parts and tank at setup.
- Each item shows quantity, unit, approximate cost from the regional rate table, and the nearest source from `places` (section 17).
- Stored in `shopping_lists(id, plan_id, season, items jsonb, generated_at)`; the owner can tick items as bought, and ticked items can create a cost log in one tap.

