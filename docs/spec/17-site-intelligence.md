## 17. Site intelligence

From just the location and boundary, the platform collects the site facts a user usually can't answer (soil, climate, water stress, slope, market prices, distances, nearby places), shows each with its source and confidence, and asks the owner to confirm. The owner's answer always wins.

### Flow

1. Saving the parcel queues `site_profile.build(farm_id)`: all data adapters run in parallel with a 20-second overall budget; partial results are fine.
2. Each result is stored as a `site_facts` row with source, method, date and confidence.
3. The wizard shows a "We found for your land" card grouped as Soil and land, Climate, Water, Markets, Nearby. Each item offers: Looks right / Change / Not sure.
4. Confirmed or edited values are saved with source `user`. Priority when reading: user-entered → soil test → derived (newest first).
5. Facts that change the plan (soil, drainage, water) with confidence below 0.5 are asked directly as wizard questions.
6. Refresh cadence: mandi prices weekly; climate normals and groundwater class yearly; soil, elevation and land cover once; places monthly.

### Facts collected in the MVP

| Fact | Default source (via adapter) | Method | Confidence | Used by |
| --- | --- | --- | --- | --- |
| Region / agro-climatic zone | District boundaries + curated district → region table | Point in polygon | High | Crop library, templates |
| Climate normals: monthly rain, max and min temperature, hottest and coldest months, monsoon onset | Open-Meteo historical weather (last 10 years) | Monthly aggregates | High | Sowing windows, crop filter, water plan |
| Soil texture, clay %, pH, organic carbon (0–30 cm) | ISRIC SoilGrids (about 250 m) | Average over parcel, texture → `soil_type` | Medium; always labelled "likely" | Soil defaults, raised beds, crop filter |
| Elevation, slope, lower side | Copernicus DEM GLO-30 | Slope around the parcel | Medium; "unknown" for plots smaller than the data grid | Pond placement, drainage |
| Land cover within 500 m | ESA WorldCover (10 m) | Share of cropland, built-up, trees | Medium | Urban vs rural hints, spray-drift note |
| Groundwater stress class | Central Ground Water Board block categories (curated yearly table) | Block lookup | High, but block-level | Water warnings, water penalty in crop scoring |
| Mandi prices per crop | Agmarknet daily prices via data.gov.in (ingested into `mandi_prices`) | Median modal price over the last 12 months, same-season months, 3 nearest mandis that report the crop | Medium; fallback to state median, then library default | Crop value score, income estimates |
| Distance and drive time to nearest mandis, nearest town, Indore city | OSRM routing on OpenStreetMap (self-hosted) | Road distance and time | High where roads are mapped | Transport cost, direct-sale feasibility |
| Transport cost per kg to each market | Rate table in `settings` (Rs per km per quintal) | Distance × rate | Medium | Net price after transport |
| Nearby places: KVK, nurseries, input shops, gaushalas, cold storage, FPOs | Curated `places` table for the Indore region + OpenStreetMap | Top 3 of each within 25 km | Curated high; OSM low | Shopping list sources, AI answers |
| Possible subsidies (drip, solar pump, horticulture) | Curated `schemes` table by state and district | Simple rules | Medium; "check with the office" | Note beside setup cost; never subtracted automatically |
| Local daily wage and common input prices | Curated regional rates; later refined from users' cost logs | Lookup | Low to medium | Running cost estimate |

### Tables

```sql
site_facts(id, farm_id, key text, value jsonb, unit text null,
           source text,                 -- 'open_meteo','soilgrids','dem','worldcover','cgwb','agmarknet','osrm','places','user','soil_test'
           method text, confidence numeric, fetched_at timestamptz, expires_at timestamptz,
           status text check (status in ('derived','confirmed','edited','rejected')),
           unique(farm_id, key, source))
-- view site_profiles: one winning value per farm and key (user > soil_test > derived, newest first)
mandis(id, name, district, state, geom geometry(Point,4326), agmarknet_code, region_id)
mandi_prices(id, mandi_id, crop_id, price_date date, min_paise, max_paise, modal_paise, unit)
places(id, kind text, name, name_hi, geom geometry(Point,4326), phone null, source text, verified bool, region_id)
schemes(id, region_id, name_en, name_hi, applies_to text, rule jsonb, office text, url text, checked_on date)
geo_cache(cell_key text, source text, payload jsonb, fetched_at timestamptz, primary key(cell_key, source))
```

### Rules

- Every source is an adapter implementing `fetch(parcel) -> list[Fact]`, with a fake for tests, registered in the "site data sources" registry (section 16). A failing adapter returns nothing and logs; it never blocks setup.
- Cache results by 0.01° grid cell and source so nearby farms reuse them; respect each source's rate limits and licence, store its attribution, and show attributions on the site profile screen.
- Refreshes never overwrite `confirmed` or `edited` facts; if new derived data differs a lot, show "new data available" to the owner.
- Sanity ranges reject implausible values (e.g. annual rain below 100 mm or above 5,000 mm for MP) and mark them low confidence.
- Soil facts always carry "estimated from public data; confirm with a Soil Health Card test", and a test result, once entered, replaces them.
- Mandi prices ingest as a scheduled job into our own tables; plans read our tables, never the live API.

### Acceptance for this module

- [ ] For 10 test locations around Indore (including an urban Bijalpur plot, 4 villages 30–70 km away and a terrace), a profile builds in under 20 seconds with climate, soil, 3 mandis and distances.
- [ ] Every fact shows its source and date; changing any value regenerates the plan with it.
- [ ] With every adapter switched off, setup still completes using wizard questions.
