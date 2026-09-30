---
name: write-migration
description: Write an Alembic migration following expand -> migrate data -> contract. Use for any schema change.
---

# write-migration

1. Identify the phase: **expand** (add nullable columns/tables/indexes), **migrate** (backfill data), or **contract** (drop/rename). Each phase ships in a separate release.
2. Never drop or rename a column/table in the same release that stops using it. If the request needs that, split it and explain.
3. Create with `alembic revision -m "<phase>: <what>"` under `backend/app/db/migrations/versions/`. Include a working `downgrade` where feasible.
4. Conventions (spec §5): uuid pk, `created_at/updated_at` timestamptz UTC, `created_by` where users write, `deleted_at` for user content, GiST index on geometry columns, geometry `geometry(Polygon,4326)`.
5. Only edit migrations not listed in `backend/app/db/migrations/APPLIED`. Applied ones are immutable (a hook blocks edits).
6. Test: `make migrate` on a fresh DB, then downgrade/upgrade once; run integration tests.
7. After a migration is released, add its revision id to `APPLIED`.
