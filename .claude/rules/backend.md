---
paths:
  - "backend/**"
---

# Backend rules

- Python 3.12, FastAPI, Pydantic v2, SQLAlchemy 2 **async**, Alembic. `mypy --strict` must pass; ruff formats.
- Module shape (spec §16): `api.py` (routes only), `service.py` (the only public entry point), `schemas.py`, `repository.py` (only place with DB access), `events.py`, `tests/`, README. Use `make new-module`.
- Never import another module's repository/models. Call its `service.py` or publish an event to the `outbox` table in the same transaction. import-linter contracts enforce this.
- Outside services (LLM, embeddings, storage, channels, weather, geocode, email) only through `app/adapters/`; no provider SDK imports elsewhere. Each adapter: interface, implementation, fake, registry entry, config switch.
- Migrations: Alembic expand → migrate data → contract across separate releases. Never drop/rename a column in the release that stops using it. Applied migrations are listed in `backend/app/db/migrations/APPLIED` and are immutable.
- Authorisation: every farm route uses the single `require_farm_role` dependency. Money fields are stripped for caretakers without `caretaker_sees_money`.
- Errors use the §12 format: `{"error": {"code", "message_key", "details"}}`; no raw user-facing text.
- Tunable numbers come from the `settings` table (cached 5 min) or the crop library; never constants.
- Money integer paise; UTC timestamps; parameterised queries only; log with `request_id`, `farm_id`, `user_id`.
- Coverage: engine and profit ≥ 90%, overall ≥ 75%.
