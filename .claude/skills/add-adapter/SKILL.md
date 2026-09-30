---
name: add-adapter
description: Add an outside-service adapter (LLM, embeddings, storage, channel, weather, geocode, site-data source, email). Use whenever code needs a third-party service or provider SDK.
---

# add-adapter

1. Check the provider against the §4 selection rules (licence, maintenance, official Docker image, replaceable). Record any exception in `docs/decisions.md`.
2. In `backend/app/adapters/<kind>/`:
   - `base.py` — the interface (Protocol/ABC); for site data sources: `fetch(parcel) -> list[Fact]`
   - `<provider>.py` — real implementation; the ONLY place the provider SDK is imported
   - `fake.py` — deterministic fake for tests
3. Register in the `<kind>` registry keyed by string name.
4. Add the config switch (e.g. `LLM_PROVIDER`) to settings and `.env.example` (dummy values only).
5. Failing adapters must log and degrade (site-data adapters return nothing; never block setup). Respect rate limits; store attribution where the source requires it.
6. Tests: interface contract test run against both fake and (mocked) real implementation; no network in unit tests.
7. Run `make lint typecheck test`.
