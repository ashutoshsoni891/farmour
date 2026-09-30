---
name: new-module
description: Scaffold a new backend module in the spec section 16 shape and register it. Use when adding a module under backend/app/modules/ (e.g. "add a records module", "make new-module NAME=x").
---

# new-module

1. Confirm the module is in the spec §3/§16 list (or record why in `docs/decisions.md`). Name is lowercase snake_case.
2. Create `backend/app/modules/<name>/` with:
   - `api.py` — FastAPI router only; uses `require_farm_role`; errors in §12 format
   - `service.py` — the only public entry point
   - `schemas.py` — Pydantic v2 contracts
   - `repository.py` — only DB access; touches only this module's tables
   - `events.py` — event names/versions published and consumed (IDs only, via `outbox`)
   - `tests/` — `test_service.py` (unit) and `test_api.py` (integration, real Postgres+PostGIS)
   - `README.md` — purpose, public service functions, events published/consumed, settings used
   - `__init__.py`
3. Register the router in `backend/app/api/` and add the module to the import-linter contracts (`importlinter` config) so no other module may import its repository/models.
4. Add/adjust the `make new-module` target if the scaffold script changed.
5. Run `make lint typecheck test`; all must pass.
6. Record structural choices in `docs/decisions.md`.
