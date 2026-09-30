# identity

**Purpose:** who the caller is. Validates Keycloak access tokens (owners, agronomists, admins),
issues caretaker sessions from single-use login links, stores profiles (language, unit
preference) and lets admins grant roles.

**Owns tables:** `users`, `channel_accounts`, `login_links`.

**Public service functions** (`service.py`):
- `current_user` / `CurrentUser` — FastAPI dependency returning a `Principal`
- `require_admin` / `AdminUser` — dependency for admin routes
- `get_me`, `update_me`
- `request_login_link`, `verify_login_link`
- `list_users`, `admin_update_user`
- `user_exists` — for other modules

**Events:** publishes none; consumes none.

**Settings used:** `auth.link_ttl_minutes`, `auth.link_rate_limit`, `auth.caretaker_session_days`.

**Notes:** roles come from the `users` flags, not Keycloak token roles. The first admin is
created with `uv run python -m app.cli make-admin <email>`.
