# Telegram verification report

Implementation is saved on `codex/self-hosted-n8n`. No existing Telegram bot was contacted or changed. No real credentials were available to this cloud task. The 14 workflow JSON exports, their 327 executable nodes, Windows scripts and existing private configuration are unchanged.

| Check | Result | Evidence / limits |
| --- | --- | --- |
| Complete Python regression suite | PASS | 133 passed; 1 native Windows ACL test skipped. Existing CRM, appointments, tenant isolation, integrations, enterprise modules and workflow preservation tests included. |
| Telegram integration tests | PASS | 20 tests, including parameterized malformed updates. Mocked official API; no live bot. |
| Incoming text, /start, returning-customer CRM synchronization and inventory matching | PASS | Authenticated updates and repeated IDs tested; actual inventory records used. |
| Guided properties, slots and explicit confirmation | PASS | Shared availability and booking checks; cross-customer tokens, duplicate confirmation and conflicting slots rejected. |
| Arabic/English, internal mode metadata, consent and human handoff | PASS | Shared CRM controls; automatic replies suppressed while human owns conversation; Arabic follow-ups and stop tested. |
| Poller lease, durable offsets and duplicate-safe outbound queue | PASS | Mocked getUpdates/sendMessage; two owners cannot hold one bot lease; resumed offset and one outbound send asserted. |
| Rate limits, network uncertainty and n8n reconciliation | PASS | Telegram retry_after respected; uncertain outcomes not replayed; existing reconcile endpoint drains only authorized Telegram delivery. |
| Secret storage, validation, logging and delivery authorization | PASS | Private 0600 file; no credential echo; bot URL redaction; webhook registration requires consent; in-flight verification cannot restore a revoked permission. |
| Frontend localization unit suite | PASS | 4 tests; new Telegram UI covered by missing-translation checks. |
| Frontend TypeScript / production build | PASS | Build completed. |
| Browser Telegram demo → Unified Inbox and bilingual form persistence | PASS | Chromium/Playwright passed against both the native fixture and final Docker app; fictional data, no screenshots generated. |
| Cloud/Linux Docker runtime using cached pinned dependencies | PASS | Current source and built frontend layered over the previously verified runtime (FastAPI 0.143.0, httpx 0.28.1); non-root UID 10001, health, frontend, fictional matching/deduplication and idle poller checked. |
| Fresh repository Dockerfile dependency installation | BLOCKED | Docker build containers could not resolve package hosts, including a host-network retry. TLS/package verification was not weakened and repository Docker configuration was not changed. |
| Windows PowerShell 5.1 / Docker Desktop execution | NOT VERIFIED | No Windows machine was available. Existing launcher regressions passed on Linux where applicable; native ACL test skipped. |
| Owner's existing local n8n | NOT VERIFIED | Cloud did not access the owner's localhost. Workflow exports remain byte-for-byte unchanged. |
| Live Telegram receive-and-reply, official webhook delivery and customer messaging | NOT VERIFIED | Requires the owner's token configured locally and explicit Enable authorization. Mocked tests do not establish live success. |

No customer database, Docker volume, `.env`, n8n data or existing bot configuration was modified. Disposable container/native test fixtures contain fictional data only. No real external messages or paid model requests were sent. The only remaining deployment actions are the owner's local update, private token entry, Connect and explicit Enable; then send a real Telegram message to verify its receipt and reply.

See [exact Windows and bot setup steps](telegram-integration.md).

## Customer-facing polish verification

- **147 Python tests passed; one native Windows ACL test skipped.** This includes 28 Telegram tests for storage, consent, polling, deduplication, handoff, booking and message formatting.
- **Four frontend unit tests, TypeScript/production build and the existing Telegram browser journey passed.**
- New regression coverage verifies no technical prefixes on generated replies/history/outbox, multiline inventory-only property blocks, safe plain-text transport and Arabic direction isolation, correct Arabic/English weekday/month names, Cairo winter/summer UTC offsets and the autumn repeated hour, workspace-zone overrides/Cairo fallback, natural slot buttons and selection/confirmation/history/reminder text, preserved ISO storage and confirmed references, explicit confirmation, rejection of conflicting bookings, and the contact-agent action.
- Mocked provider delivery queries the database before accepting a success message, verifying that the booking is committed before dispatch. No real Telegram message was sent by these tests. The owner reports the prior bot works live; this formatting release remains independently **NOT VERIFIED** through live Telegram delivery or on Windows.
- Historic messages and already queued replies are not rewritten. No credential/polling/delivery adapter, Docker/Windows tool, seed data or n8n export changes.

Changed files: `backend/telegram.py`, `backend/telegram_conversation.py`, `backend/telegram_messages.py`, `backend/assistant.py`, `backend/domain.py`, `tests/test_telegram.py`, `tests/test_telegram_messages.py`, `docs/telegram-integration.md`, `docs/telegram-verification.md`.

Deploy using the existing `Update-Madar.cmd`. No additional dependency, bot reconfiguration or data reset is required.
