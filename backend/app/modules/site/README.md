# site

**Purpose:** TODO

**Owns tables:** none yet.

**Public service functions** (`service.py`): none yet.

**Events:** publishes none; consumes none.

**Settings used:** none.

**Schemes:** owns `schemes` (government schemes and benefits, cited, status like the crop library). `schemes_for(tags, farm)` matches a plan and farm to schemes with structured rules; seed `seeds/site/schemes.json`, loaded by `load-site-data`.

**Cost norms and KVKs:** owns `cost_norms` (setup cost and subsidy rate per component, from MIDH 2025) and `kvks` (Krishi Vigyan Kendra contacts for Madhya Pradesh); both cited and checked like schemes, seeds `seeds/site/cost_norms.json` and `kvks.json`, read at `GET /api/v1/cost-norms` and `GET /api/v1/kvks?district=`.
