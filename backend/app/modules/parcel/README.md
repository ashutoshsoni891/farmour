# parcel

**Purpose:** a farm's plot: boundary, area, gate, soil/drainage/slope and obstacles.

**Owns tables:** `parcels` (PostGIS polygon, GiST index).

**Public service functions** (`service.py`): `get_parcel`, `save_parcel` (GeoJSON boundary),
`save_from_measurements` (rectangle or four sides + diagonal), `parcel_exists`.

**Geometry:** stored EPSG:4326, measured in EPSG:32643 (`geometry.py`, pure functions).
Validation (min/max area, shortest side, self-intersection) uses the `parcel.limits` setting.

**Events:** publishes `parcel.saved`; consumes none.

**Settings used:** `parcel.limits`.
