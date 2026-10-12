# Sample inventory in the real Telegram workspace

## Windows: update, confirm, demonstrate

From PowerShell in your existing MADAR repository:

```powershell
.\Update-Madar.cmd
```

The existing updater rebuilds and launches MADAR with its saved local configuration and existing Docker volume. It does not create a second n8n instance. Sign in as the administrator of **workspace `madar`**, open **Company settings → Sample business data → Load Sample Business Data**, read the confirmation, tick the acknowledgement, and select **Confirm import**. Arabic: **إعدادات الشركة → بيانات أعمال تجريبية → تحميل بيانات أعمال تجريبية**. This action is deliberately not run automatically by startup or an update.

The import creates copies of the existing fictional portfolio: 30 listings with the same 30 bundled WebP images, 40 customers, 25 four-message conversations, 15 viewing examples, 20 tasks and five sample staff profiles. Listings retain their fictional prices, requirements and availability. The isolated **Madar Estates** demo tenant is never read, overwritten or reset. The existing dataset builder runs in an in-memory database; only its business records are copied. Images remain locally bundled, never hotlinked.

No Telegram reconnect or token re-entry is needed. Existing polling leases, offsets, permissions, private token storage and other provider settings remain unchanged. Actual inbound Telegram interactions continue through the existing CRM/inbox/availability/explicit-confirmation transaction.

### Short local Telegram check

Use your own customer Telegram account and the **already authorized, connected bot**:

1. Send `/start`, then `Buy an apartment in New Cairo, budget 5 million, 3 bedrooms` (or `عايز شقة في التجمع، ميزانيتي خمسة مليون وتلات غرف`). Available matching inventory should include **Palm Residence**. Replies identify sample listings as fictional.
2. Check **Leads & CRM** and **Unified inbox**: your genuine Telegram customer is separate from the prefixed sample customers, and both incoming/outgoing history are linked to that customer. Returning messages reuse the same lead.
3. Choose the property's **View** button, select an offered future time, then explicitly **Confirm booking**. Before confirmation there is no new booking. After persistence, the reply includes its booking reference, local date/time and an agent button.
4. Check **Appointments**, the customer's CRM history, **Follow-up tasks** and **Analytics**. The genuine customer interaction is counted; imported example customers/viewings are excluded from business metrics. The viewing uses a fictional property, is labelled as a demonstration and does not represent a reservation of a real listing. Nothing is sent to an external calendar. `/appointments` shows your own persisted viewing.

If your bot has delivery disabled, use **Company settings → Telegram guided setup** to explicitly enable the existing verified connection before the customer test. Loading sample data never changes this permission. No public tunnel or webhook registration is needed for existing long polling. These steps require your laptop; Cloud tests cannot verify delivery against it.

## Safety model

- Administrator-only load/remove APIs are limited to non-demo workspace slug `madar`, with strict boolean confirmation, existing session/origin protections and `BEGIN IMMEDIATE` transactions.
- Separate additive `sample_datasets` / `sample_records` tables track every imported business row. Stable namespaced IDs preserve all customer/property/staff/task/conversation/viewing relationships. A second import is a no-op, including records subsequently edited in the application. A collision rolls back the entire import and never adopts or overwrites another record.
- Every sample customer/staff name, stored message, task and appointment is marked **Sample / Fictional**. Property cards, API metadata and Telegram recommendations identify fictional inventory and illustrative synthetic photos. Real Telegram leads keep genuine contact IDs and receive no imported sample marker.
- Contacts have empty phone numbers, reserved `sample.invalid` emails and new `sandbox:sample-…` identities. No demo Telegram chat IDs, contacts, credentials, sessions, delivery queues or webhook records cross into the real workspace.
- Sample staff use inactive, permanently unusable authentication placeholders in the existing staff table solely to preserve display/appointment relationships. No password is generated and no access is granted. Login and session authentication exclude tracked sample staff even if someone changes their active flag directly; real lead assignment, slots and bookings also exclude them. Real bookings use active genuine staff (including the workspace owner).
- Import inserts database rows directly: it never calls chat providers, n8n, calendars, webhooks, notification senders or poller management. Sample leads are skipped by periodic follow-ups/reminders/retention and availability notifications; manual sample replies stay in the inbox. The provider dispatcher also rejects sample leads if a contact ID is later rewritten.
- Analytics use persisted genuine records. Imported sample activity is excluded from sources, pipeline, response times, appointments, follow-up completion and revenue. Deals involving sample properties also cannot contribute revenue/sales volume. The loaded dataset's separate displayed counts come from persisted tracked rows, not fixed marketing numbers. Genuine customer viewings on fictional inventory remain recorded interactions, visibly described as demonstration viewings.

## Safe removal

In the same settings section, select **Remove Sample Business Data**, acknowledge and confirm. This deletes only tracked imported records and their provenance, never unrelated records or the isolated demo workspace. It does not delete images or alter secrets, Docker volumes, n8n workflows or Telegram configuration.

Removal is blocked **as a whole** if genuine/untracked records depend on sample customers, properties, staff, tasks or appointments. Checks include appointments (also cancelled/completed), deals, messages, outbox/history, sessions and pending unexpired Telegram selections. Even a malformed legacy cross-tenant foreign key blocks destructive cascading. The UI explains this and the status API reports dependency counts without exposing customer identities or credentials. Checks repeat inside the deletion transaction to handle bookings occurring after the page was loaded.

After a genuine viewing is linked to a sample property, keep that property/dataset. Cancelling the viewing does not remove its historical dependency. Resolve dependencies through appropriate record management/support; the sample action never deletes real history or silently detaches its inventory. If new history has been added to sample customers, that history is protected too. Removing and later reloading an unreferenced dataset is supported.

## Developer checks

With backend development dependencies, frontend dependencies and Chromium installed:

```bash
.venv/bin/python -m pytest -q
cd frontend
npm run test:unit
npm run build
cd ..
.venv/bin/python scripts/test_browser.py
```

The browser runner uses a fresh disposable database/server per test file, clears provider credentials, disables polling/external sends/model usage/n8n, and retains production login rate limits. It never uses an existing owner database. `MADAR_CHROMIUM_PATH` can select the browser executable. Python/Node are development test dependencies, not new Windows launcher requirements. See [verification scope](sample-business-verification.md).
