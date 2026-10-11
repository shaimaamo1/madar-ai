# Telegram integration for local MADAR AI

Telegram runs inside the existing MADAR app container using outbound HTTPS long polling. No public URL, extra container, PowerShell edits, n8n JSON edits or tunnel are needed. The existing 14 workflow exports and 327 nodes are unchanged.

## Windows: update and connect

1. Open PowerShell in the existing MADAR repository and run:

   ```powershell
   .\Update-Madar.cmd
   ```

2. Sign in to the **actual `madar` administrator workspace**, then open **Company settings → Telegram guided setup** (also available under Integrations).
3. Enter the dedicated bot token in the password field and click **Save and Connect**. Leave the public HTTPS origin blank. The field clears immediately; the server verifies the bot and starts receiving updates. **Test bot connectivity** performs read-only identity verification. If the selected bot already has a webhook, replacement requires the explicit authorization checkbox; no other bot is touched.
4. Check the authorization checkbox and click **Enable Telegram delivery** when ready to allow real replies. This permission is separate from WhatsApp, other external delivery and paid AI permissions.
5. Open that bot in Telegram and send `/start`, then a property inquiry such as `Buy an apartment in New Cairo, budget 5 million, 3 bedrooms` or `عايز شقة في التجمع، ميزانية خمسة مليون، تلات غرف`. Check that a reply arrives and the conversation appears in Unified Inbox. This local receive-and-reply check is required before claiming live Telegram works.

**Disable Telegram delivery** stops sends but keeps receiving; **Disconnect bot** stops polling and disables sending. An existing webhook managed by this setup is removed only for the configured bot. Existing pending updates are never dropped automatically. Replacing the token requires disconnecting first. The integration controls are restricted to the bound non-demo administrator workspace.

## Customer experience

Supported commands: `/start`, `/properties`, `/appointments`, `/agent`, `/help`, `/subscribe`, `/stop`, plus `/handoff` and `/status`. A persistent menu exposes the main commands. Available property recommendations include inventory-backed prices and viewing buttons. Selecting a property shows available slots in the company's timezone. Selecting a slot shows **Not booked yet** and a confirmation button. Only explicit confirmation invokes MADAR's existing transaction-protected booking function, which rechecks inventory, adviser availability and conflicts. Expired, replayed or another customer's selections cannot book.

English and Egyptian Arabic share existing preference extraction, actual inventory matching, consent and handoff rules. Telegram remembers the conversation language for commands and callbacks. Without an authorized model, replies are visibly labeled **Deterministic assistant / مساعد آلي بقواعد محددة**. An authorized model may interpret preferences; inventory facts and booking authority remain deterministic. No invented listings, prices or bookings are generated.

`/agent` records human ownership and acknowledges the handoff; subsequent automatic replies and queued automatic delivery are suppressed until an adviser releases the conversation. Human messages entered through the existing Unified Inbox use the same permission-gated outbox. `/subscribe` explicitly grants follow-up consent; `/stop` revokes it and holds queued messages. Proactive messages require consent. Fictional `sandbox:` contacts can never receive provider messages.

## Security and reliability

- The token and generated webhook secret are stored in `telegram-private.json` beside the database, normally `/app/var/telegram-private.json` in the existing Docker data volume. The file is atomically written with mode `0600` by the non-root app user. It is outside Git; it is not placed in workflow exports, browser storage, frontend responses or `.env`. Storage is permission-protected, **not encrypted at rest**: protect Docker Desktop/data-volume access and treat backups containing this file as secret material.
- Only masked input is used; malformed setup errors omit submitted values. HTTP client logging filters redact Telegram Bot API URL tokens. Connection exceptions and provider response bodies are never surfaced as diagnostics.
- Delivery defaults off. `MADAR_ALLOW_TELEGRAM_SEND=false` is the optional environment fallback; dashboard configuration takes precedence once saved. `MADAR_ALLOW_EXTERNAL_SEND` retains its existing controls for WhatsApp and other providers. Enabling Telegram changes no other permission.
- Polling uses one persisted bot/tenant lease in SQLite and resumes from a durable update offset after restart. The receipt, CRM/messages/outbox effects and offset commit together. Multiple MADAR workers sharing the same database cannot poll simultaneously. Do not run the same bot from separate databases or external pollers: Telegram conflict responses stop this poller and disable its delivery rather than competing indefinitely. Authentication failures also disable the connection.
- The shared outbox claims each send atomically. Telegram `retry_after` pauses the channel and schedules bounded retries. Network timeouts become **Uncertain** and require reconciliation rather than automatic replay. Interrupted sends are escalated by the existing n8n reconciliation workflow. Follow-ups reuse existing n8n scheduling and consent logic; the poller drains due replies/retries without needing n8n for each incoming message.
- Existing n8n **MADAR Follow-up Scheduler** queues eligible follow-ups; **MADAR Delivery Reconciliation** records failures and drains Telegram only when its dedicated permission is enabled. Telegram input goes directly to MADAR's shared business services; do not also wire a Telegram Trigger to the same bot/update stream. That would introduce a second consumer.
- Deploy one app process per data volume for the current SQLite architecture. Keep Windows startup/update tools and the existing n8n container/data as they are.

## Safe demo

Use **Open interactive demo → Company settings → Telegram guided setup**. Simulate an update without credentials or external calls. Reuse its Update ID to test deduplication, and use new IDs for the next message. CRM, matching, conversation history, consent and handoff operate in that isolated fictional workspace. Automated integration tests additionally execute property/slot/confirmation callbacks. No provider delivery is queued by the demo endpoint.

## Future HTTPS webhook option

Polling is the default. If you later authorize public hosting, use a valid public HTTPS origin and a reverse proxy/tunnel that exposes **only `/webhooks/telegram`**. Keep the dashboard, `/api` and n8n private. No tunnel is installed or opened by MADAR. Save the origin, verify the bot, explicitly authorize and select **Register authorized webhook**. Registration stops local polling and sets `allowed_updates` for messages/callbacks, a generated `secret_token`, and `drop_pending_updates=false`. Incoming requests require the exact `X-Telegram-Bot-Api-Secret-Token`; malformed and oversized updates are rejected. Return to polling through Connect; webhook replacement requires explicit authorization.

See [verification results](telegram-verification.md) for tested versus unverified functionality.
