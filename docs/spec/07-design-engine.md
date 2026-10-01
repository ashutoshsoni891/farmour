## 7. Design engine

The engine is deterministic and rule-based: the same inputs and library version always give the same plan. The LLM only explains the result in plain language afterwards. Target: under 10 seconds for 2 acres.

### Pipeline

1. **Validate** the polygon: simple (no self-intersection), 5 sqm ≤ area ≤ 20,250 sqm (5 acres; MVP cap), no side shorter than 1 m. Reject with a specific error code (section 12).
2. **Project** to UTM 43N (EPSG:32643) for all metric work; convert back to WGS84 for storage.
3. **Subtract obstacles** (trees, tank, stairs, existing structures) with a 0.5 m buffer.
4. **Orient:** true north = map north corrected by `north_bearing_deg`. Compute the minimum rotated rectangle to find the plot's main axis.
5. **Pick a template** by site type and area (table below).
6. **Carve zones** in this order: border → north strip (tall zone) → water → utility and nursery → beds → rotation.
7. **Lay out beds** inside the beds zone.
8. **Assign crops to layers** per bed and season.
9. **Check water and load;** adjust.
10. **Estimate** costs, yields and income; build the plan summary.
11. **Verify invariants** (section 5) and save as a `draft` plan.

Before choosing a template, the engine loads the farm's site profile (section 17): confirmed soil, drainage, slope, climate normals, groundwater class, local mandi prices and transport cost replace generic defaults in every rule below. Crop value uses local net price (median mandi or direct price minus transport cost); the water penalty doubles when the groundwater class is critical or over-exploited.

### Templates and zone shares

| Template | Applies when | Beds | Orchard / canopy | Rotation | Border | Water | Utility + nursery | Paths |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| T — terrace | `site_type = terrace` | 55% (planters) | in drums on edges | — | — | tank only | 10% | 35% |
| S — small plot | ground, < 150 sqm | 65% | 12% | — | 10% | tank only | 13% | inside beds zone |
| M — medium | 150–2,000 sqm | 45% | 20% | — | 10% | 5% | 12% | 8% |
| L — large | 2,000–20,250 sqm | 35% | 25% | 20% | 8% | 7% | 5% | inside zones |

Shares are defaults in `rules`; the owner can adjust each zone ±10 percentage points in the editor, and the engine re-runs.

### Zone placement rules

- **Border:** inward buffer of the parcel boundary. Width: S 0.6 m, M 1.0 m, L 2.0 m. Skip the gate segment (user marks the gate; default = the south-most edge midpoint).
- **North strip (orchard, canopy, utility):** split the remaining polygon with a line perpendicular to true north; binary-search the line offset until the northern piece matches the target area ±2%. Tall crops (height > 2 m) may only be placed here.
- **Water:** at the lowest point if `slope_dir` is set, else adjacent to the utility zone. Pond size = 30 days of peak-month demand, capped by the zone share; for S and T it is a tank, not a pond.
- **Utility and nursery:** nursery adjacent to the gate; utility (compost, drums) adjacent to water and away from the gate if space allows.
- **Rotation field (L only):** the largest remaining rectangle-like piece away from the north strip.
- If a zone cannot fit, drop zones in this order and record a warning: rotation → water pond (fall back to tank) → orchard (fall back to canopy crops in beds).

### Bed layout rules

- Default bed width 1.2 m, path 0.6 m, max bed length 10 m (a cross path of 0.6 m every 10 m); all from `settings`.
- Bed long axis runs north–south (±15°). If the beds zone is narrower than 3 m in that direction, run beds along the zone's main axis instead and record a warning.
- Tile rectangles across the zone, clip to the zone, drop pieces under 2 sqm or narrower than 0.9 m. Number beds B1, B2... from the gate side.
- Raised beds (`raised = true`) when `drainage = waterlogs` or soil is black / clay.
- Mark beds for a trellis (`has_trellis`) in alternate rows so climbers do not shade each other; trellis height 2.1 m.

### Terrace rules (template T)

- `terrace_load_kg_per_sqm` is mandatory; show a blocking notice asking the owner to get it from a structural engineer.
- Allowed media depth (m) = (load × 0.8) ÷ wet media density (default 550 kg/m³ for a cocopeat mix; `settings`). Cap container depth at this value; crops needing deeper containers are excluded.
- Heavy planters only within 1 m of the parapet; the centre is paths and light grow bags. Canopy plants only in drums in corners. No pond.

### Crop assignment

For each bed and each season covered by the plan (12 months from `start_date`), fill layers underground → surface → middle → climber (climber only on trellis beds).

**Hard constraints (a candidate is rejected if any fails):**

- Status `approved`; season and sow window reachable from the start date.
- Layer allowed for the crop; height fits the zone rule.
- Terrace: `terrace_ok` and container depth ≥ `min_container_depth_cm`.
- `drainage = waterlogs` → only `waterlogging_tolerant` crops unless the bed is raised.
- No `avoid` companion pair within one bed in the same season.
- Rotation: no crop of the same `family` in the same bed in consecutive seasons.

**Score** = 0.4 × value + 0.3 × diversity + 0.2 × ease − 0.1 × water. Weights come from `rules` and shift with the goal: `income` raises value to 0.55; `home_food` raises diversity to 0.45.

- value = expected yield per sqm × direct price, normalised 0–1 across candidates.
- diversity = 1 if the crop is not yet used elsewhere in the plan this season, else 0.3.
- ease = 1 for low-care crops (library flag), else 0.5.
- water = normalised water need.

Select greedily with a fixed tie-break (crop slug) so results are reproducible. Require at least 6 distinct crops per season for M and L, 4 for S and T.

### Quantities, water and estimates

- Plant count per layer = floor(bed length ÷ plant spacing) × rows that fit the bed width.
- Expected yield = bed area × `expected_yield_kg_per_sqm` × layer factor (multilayer crowding factor from `rules`, agronomist-set; default 0.7 for underground and surface, 0.8 for middle and climber).
- Peak water demand = sum over plantings of area × stage water. If it exceeds `water_summer_lpd`, swap the highest-water crops for lower ones in zaid until it fits; if still over, warn.
- Setup cost = zone area × cost per sqm by zone kind (`settings`, INR) plus fixed items (tank, drip kit). Every money figure in the summary is labelled "estimate".

### Engine output (stored in `plans.summary` and child tables)

```json
{
  "engine_version": "1.0.0",
  "template": "M",
  "area_sqm": 74.3,
  "zones": [{"kind": "beds", "area_sqm": 33.4, "bed_codes": ["B1", "B2", "B3"]}],
  "beds": [{"code": "B1", "length_m": 7.3, "width_m": 1.2, "raised": true, "has_trellis": true,
            "layers": {"rabi": {"underground": "carrot", "surface": "spinach", "middle": "tomato", "climber": "peas"}}}],
  "water": {"peak_lpd": 310, "available_lpd": 500, "ok": true},
  "estimates": {"setup_paise": 4200000, "yearly_cost_paise": 900000, "yearly_yield_kg": 380},
  "warnings": [{"code": "BEDS_ALONG_MAIN_AXIS", "message_key": "warn.beds_axis"}]
}
```

**Golden tests:** keep 10 reference parcels (rectangle, L-shape, triangle, narrow strip, terrace, 800 sq ft Bijalpur-style plot, 1 acre, 2 acres irregular, plot with a tree obstacle, waterlogging plot) with expected outputs reviewed by the agronomist. Any engine change must pass them or update them with review.

