---
paths:
  - "backend/app/modules/layout/**"
---

# Design engine rules (spec §7)

- Deterministic and rule-based: same inputs + same library version → same plan. No LLM, no randomness, no wall-clock in decisions. Fixed tie-break by crop slug.
- Library-driven: zone shares, widths, scoring weights, crowding factors come from `rules`/`settings`/crop library, never literals. Missing agronomy data → exclude the candidate and warn; never invent values.
- Geometry: store EPSG:4326, compute in EPSG:32643 (pyproj + Shapely 2). Convert back for storage.
- Follow the pipeline order in §7 (validate → project → obstacles → orient → template → zones → beds → crops → water/load → estimate → invariants).
- Verify §5 invariants after generation: beds within zones, zones within parcel, no overlaps.
- Every change requires golden tests (10 reference parcels, zone areas ±2%) and Hypothesis property tests (no beds outside parcel, no overlapping zones, no bed narrower than 0.9 m).
- Bump `engine_version` on any behaviour change; active plans keep their old version.
- Targets: < 10 s for 2 acres, < 3 s under 1,000 sqm.
