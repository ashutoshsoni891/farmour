# farms

**Purpose:** farms, their members and roles, caretaker invites, and the row-level access
check every farm-scoped route uses.

**Owns tables:** `farms`, `farm_members`, `invites`, `organizations` (unused in the MVP).

**Public service functions** (`service.py`):
- `require_farm_role(*roles)` / `membership(*roles)` — the single farm authorisation
  dependency; returns a `Membership` with `role` and `can_see_money`
- `create_farm`, `list_my_farms`, `get_farm`, `update_farm`, `delete_farm` (soft)
- `list_members`, `update_member` (toggle `caretaker_sees_money`)
- `invite_caretaker` — creates a shareable invite link (acceptance arrives in M5)

**Money visibility:** `to_out` nulls every money field for caretakers without
`caretaker_sees_money`. Add new money fields to `MONEY_FIELDS`.

**Events:** publishes none; consumes none.

**Settings used:** `invites.ttl_days`.
