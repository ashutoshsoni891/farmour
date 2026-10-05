# layout

**Purpose:** the deterministic design engine (spec section 7). Turns a farm's plot into a draft plan: zones (border, orchard/tall crops, pond, nursery, utility, rotation field, beds) and numbered beds. Crop assignment, water and estimates are the next M3 slices.

**Owns tables:** `plans`, `zones`, `beds` (PostGIS polygons, GiST indexes).

**Public service functions** (`service.py`): `generate_plan` (owner; new draft version, older drafts archived), `get_plan` (latest).

**Engine** (`engine.py`, pure, no database): validate -> project to UTM 43N and rotate so north is up -> subtract obstacles -> template S/M/L by area -> carve border, north strip, pond, nursery, utility, rotation -> tile beds -> verify invariants. Same plot and parameters give the same layout. `ENGINE_VERSION` is bumped on any behaviour change.

**Parameters:** library `rules` (`engine.bed`, `engine.parcel`, `engine.border`, `engine.template.S/M/L`) read through `library.service.engine_rules`; `settings` keys `layout.*`.

**Events:** none yet.
