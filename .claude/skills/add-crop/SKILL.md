---
name: add-crop
description: Add or edit a crop library entry (seed file) with all section 6 fields, status draft, no invented agronomy values. Use for any crop, variety, companion, pest or recipe seed change.
---

# add-crop

1. Open the crops seed in `backend/seeds/` and the §6 schema. The crop must be in the §6 seed list or the user must request it.
2. Fill every required §6 field: slug, `name_en`, `name_hi`, family, category, layers, seasons, `sow_windows` (Malwa), days to first harvest, harvest span, spacing, heights, sun, water need, tolerances, terrace fields, yield, prices with `price_updated_on`, `source_notes`.
3. **Never invent agronomy values.** Use only values the user supplies or that come from a cited source recorded in `source_notes`. If a value is unknown, leave it null/empty and add `TODO(agronomist): <field>`; the engine must exclude entries missing hard-constraint data.
4. Set `status: draft`. Never set `approved`, `approved_by` or `approved_at` (agronomist workflow only).
5. Provide both `en` and `hi` names; companions need `reason_en`/`reason_hi`.
6. Run the seed validation test (schema + required fields + status == draft for new entries).
7. Report which fields are TODO for agronomist review.
