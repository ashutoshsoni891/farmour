# API

The contract is `backend/openapi.json`, generated from the code (`make openapi`) and checked
in CI. Interactive docs run locally at http://localhost/api/docs.

- Prefix `/api/v1`; bearer tokens (Keycloak for owners/agronomists/admins, caretaker session
  tokens from `/auth/otp/verify`).
- Errors: `{"error": {"code", "message_key", "details"}}` (spec section 12).
- Farm routes return 404 to non-members and 403 `FORBIDDEN_ROLE` to members without the role.
- Money fields are `null` for caretakers without `caretaker_sees_money`.
