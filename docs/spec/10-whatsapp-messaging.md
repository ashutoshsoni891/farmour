## 10. WhatsApp messaging

The messaging app is the caretaker's whole interface, so every flow must work with buttons and short replies in Hindi, with typing as a fallback. Flows are written once against a \`Channel\` interface (send text, send buttons, send list, receive reply, download media): the beta runs on the Telegram Bot API (free, inline keyboard buttons, no template approval), and WhatsApp Cloud API is added later as a second implementation. The WhatsApp rules below apply once it is switched on.

### Platform rules to respect (Meta WhatsApp Cloud API)

- Business-initiated messages outside the 24-hour customer-service window must use **pre-approved templates**; free-form and interactive messages only inside the window. Track `wa_sessions.last_inbound_at`.
- Get explicit **opt-in** when a caretaker is invited; honour "STOP" / "बंद" immediately (set `wa_opt_out`).
- Verify every webhook with `X-Hub-Signature-256` and the app secret; dedupe on `wa_message_id`; respond 200 within 5 seconds and process via the queue.
- Media (photos, voice) arrive as media IDs: download immediately to S3, since media URLs expire.
- Pricing is per message and changes over time; log every outbound message with its template name so costs can be reported. Check current Meta pricing before launch.

### Templates (register in both `en` and `hi`)

| Template | When | Quick-reply buttons |
| --- | --- | --- |
| `invite_caretaker` | Owner invites a caretaker | Join / Not now |
| `daily_tasks` | 07:00 IST, if tasks exist | All done / Some not done / Help |
| `weekly_digest` | Sunday 18:00 IST | Open plan (link) |
| `harvest_prompt` | On harvest days | Log harvest / No harvest today |
| `weather_alert` | From section 9 | OK, done / Need help |
| `overdue_summary` | Owner only, daily if overdue | Open app (link) |

Keep templates short (under 300 characters of body), with bed codes and crop names in the user's language; long lists go behind a link.

### Conversation flows (state machine in `wa_sessions.state`)

1. **All done** → mark all of today's sent tasks `done`, reply with a one-line thanks and tomorrow's count.
2. **Some not done** → send an interactive list (max 10 rows) of today's tasks; each selection toggles done / not done; a "Finished" button closes it. Unselected tasks stay pending.
3. **Log harvest** → ask "Which bed?" as a list of beds with harvest tasks → "How much?" with buttons (1 kg / 2 kg / 5 kg / Type amount) → confirm.
4. **Free text** is parsed: patterns like `B2 lauki 3 kg`, `बी 2 लौकी 3 किलो`, `seed 250 rs`. Parser order: regex rules → Hindi/English number and unit normalisation → LLM extraction with a strict JSON schema → if confidence < 0.8, ask a confirm question with buttons.
5. **Photo** → ask "Which bed?" (list) → store as `photo` log → run photo check (section 11) → reply with the result and any recipe task added.
6. **Voice note** → store in S3 as a `note` log, reply "Saved; your owner can listen to it". (Transcription is post-MVP.)
7. **Help** or any question → route to the AI helper with the farm context; answers capped at about 600 characters with an "Open in app" link for more.
8. **Unknown sender** → reply with a short explanation and no data access.

Retries: failed sends retry 3 times over 30 minutes; after that the task stays `pending` and the owner's app shows "message not delivered".

