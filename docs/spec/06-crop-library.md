## 6. Crop library

The library is the product's source of truth: the design engine, planner and AI helper read only from it. Nothing reaches users until an agronomist approves it.

### Schema

```sql
crops(id, slug unique, name_en, name_hi, family text,        -- 'cucurbit','solanaceae',...
      category text check (category in ('vegetable','leafy','root','spice','fruit_tree','fruit_short','pulse','cereal','millet','herb','border','green_manure','flower')),
      layers text[],                    -- allowed: underground/surface/middle/climber/canopy
      seasons text[],                   -- kharif/rabi/zaid/perennial
      sow_windows jsonb,                -- [{"from":"10-01","to":"11-15","method":"direct|transplant"}] Malwa
      nursery_days int null,            -- days in nursery before transplant
      days_to_first_harvest int, harvest_span_days int,
      spacing_row_cm int, spacing_plant_cm int, rows_per_1_2m_bed int,
      height_max_cm int, root_depth_cm int,
      sun text check (sun in ('full','partial','shade_tolerant')),
      water_need text check (water_need in ('low','medium','high')),
      water_l_per_sqm_day jsonb,        -- by growth stage
      heat_tolerance_c int, cold_tolerance_c int,
      waterlogging_tolerant bool, terrace_ok bool, min_container_depth_cm int null,
      expected_yield_kg_per_sqm numeric, yield_unit text default 'kg',
      price_mandi_paise_per_kg bigint, price_direct_paise_per_kg bigint, price_updated_on date,
      years_to_bear numeric null, lifespan_years int null,   -- perennials
      tree_spacing_m numeric null, canopy_diameter_m numeric null,
      status text check (status in ('draft','in_review','approved','retired')),
      approved_by null, approved_at null, source_notes text)
crop_varieties(id, crop_id, name, days_to_first_harvest, notes, status)
companions(crop_a, crop_b, relation text check (relation in ('good','avoid')), reason_en, reason_hi)
pests(id, crop_ids uuid[], name_en, name_hi, symptoms_en, symptoms_hi, months int[], recipe_ids uuid[], escalate_if text)
recipes(id, slug, name_en, name_hi,           -- jeevamrut, beejamrut, neemastra, dashparni ark, vermicompost...
        ingredients jsonb, per_area_sqm numeric, steps_en text[], steps_hi text[],
        ferment_days int null, shelf_life_days int null,
        apply_every_days int null, apply_method text, safety_notes_en, safety_notes_hi, status)
rules(id, code unique, description, params jsonb, applies_to text, status) -- engine rules, section 7
library_chunks(id, source_table, source_id, lang, text, embedding vector(1024), status)
```

### Seed list for v1 (about 60 crops, Malwa)

| Layer / role | Crops |
| --- | --- |
| Underground | Ginger, turmeric, carrot, radish, beetroot, onion, garlic, sweet potato, colocasia (arbi) |
| Surface (leafy) | Spinach, methi, coriander, amaranth, lettuce, mint, dill, mustard greens, chaulai |
| Middle | Tomato, brinjal, chilli, capsicum, okra, cabbage, cauliflower, knol-khol, cluster bean, bush beans, marigold |
| Climber | Bottle gourd, ridge gourd, sponge gourd, bitter gourd, cucumber, pointed gourd (parwal), ivy gourd (kundru), pole beans, peas, sem |
| Canopy / short fruit | Papaya, banana, drumstick (moringa) |
| Orchard | Mango, guava, custard apple, lemon, pomegranate, jamun, amla, dragon fruit |
| Rotation field | Soybean, moong, urad, chana, wheat, kodo / kutki millet, mustard |
| Border | Lemongrass, curry leaf, karonda, bamboo, vetiver |
| Green manure | Dhaincha, sunn hemp |

### Example record (illustrative values; agronomist must verify before approval)

```json
{
  "slug": "bottle-gourd", "name_en": "Bottle gourd", "name_hi": "लौकी",
  "family": "cucurbit", "category": "vegetable",
  "layers": ["climber"], "seasons": ["kharif", "zaid"],
  "sow_windows": [{"from": "02-01", "to": "03-15", "method": "direct"},
                  {"from": "06-15", "to": "07-31", "method": "direct"}],
  "days_to_first_harvest": 60, "harvest_span_days": 60,
  "spacing_plant_cm": 90, "height_max_cm": 250,
  "sun": "full", "water_need": "medium", "terrace_ok": true,
  "min_container_depth_cm": 45, "status": "draft"
}
```

### Review workflow

1. Anyone with the agronomist role creates or edits an entry → `draft`.
2. Submit → `in_review`; a different agronomist (or the same one after 24 hours for v1) approves → `approved`.
3. On approval, regenerate that entry's `library_chunks` (en + hi) and embeddings.
4. Plans record `engine_version` and library entry versions used, so a later library change never silently alters an active plan; the owner is offered "update plan" instead.
5. Prices have `price_updated_on`; the UI shows "prices older than 90 days" when stale.

