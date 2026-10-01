## 2. Users, roles and permissions

Four roles; permissions are per farm, so one person can be owner of one farm and caretaker on another.

| Role | Uses | Can do | Cannot do |
| --- | --- | --- | --- |
| Owner | Web app (PWA) | Create farms, draw parcels, generate and edit plans, invite caretakers, see all logs and money, export plans | Edit the global crop library |
| Caretaker | WhatsApp first; PWA optional | Receive tasks, mark done / skip, log harvest, cost and photos, ask the AI helper | See sale prices or profit (unless owner enables `caretaker_sees_money`), edit plans, delete logs |
| Agronomist | Web admin | Create and edit crop library entries, rules and recipes; review and approve; flag unsafe AI answers | Access individual farms unless an owner shares one for review |
| Admin | Web admin | Manage users, settings, feature flags, message templates; view audit log | — |

**Rules:**

- Auth (no SMS cost): owners, agronomists and admins log in through Keycloak (email + password, Google, or passkey). Caretakers never need a password: the owner's invite sends a one-time link that binds their Telegram (later WhatsApp) account to the farm; for the PWA they get a single-use login link in the chat. Phone number is stored as contact identity; paid SMS OTP can be added later.
- A caretaker is invited by phone number; the invite is accepted by replying on WhatsApp or opening a link. No password needed.
- Membership table `farm_members(farm_id, user_id, role)` decides access; every API call checks it.
- Every write records `created_by`, and changes to plans, library entries and money logs go to `audit_log`.

