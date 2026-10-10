# Premium upgrade verification — v1.1

Updated 10 October 2026. This upgrades the existing repository; it does not deploy a production service, activate workflows, send real messages, connect to the owner's laptop or authorize billable inference.

| Component | Result | Evidence and practical limit |
| --- | --- | --- |
| Python/API regression and integration suite | PASS | 82 passed; one native Windows ACL test explicitly skipped on Linux. Existing journeys plus migration preservation, sandbox isolation, spoken Egyptian preferences, consent history, persistent handoff, replay-bound booking, redacted incidents, reconciliation, mocked official Meta templates/status/retry cap and workflow dependency/migration checks |
| Windows orchestration | PASS | Included in the Python run: thirteen fake Windows/Docker/HTTP scenarios, sixteen simulated ACL cases and actual PowerShell Core stdin invocation. DACL-only repair, secure-ACL reuse and redacted failures covered; native Windows execution remains unverified. No laptop or n8n requests |
| TypeScript and production frontend | PASS | Type checks and Vite production build; local licensed font files bundled |
| Original browser journeys | PASS | CRM/inventory/settings/booking/public portal/mobile behavior preserved on the upgraded application |
| Complete premium browser suite | PASS | All nine journeys pass against the final app-only Docker runtime on loopback port 18112, with n8n disabled and dummy settings. Includes real font responses and browser font loading |
| Light-theme accessibility | PASS | Automated axe WCAG 2 A/AA and WCAG 2.1 AA checks on login and all thirteen dashboard pages |
| Dark-theme and Arabic mobile accessibility | PASS | Thirteen dark-theme dashboard pages plus Arabic RTL/mobile sandbox pass automated axe checks; keyboard dialog trapping/restoration and mobile overflow checks pass. Automated scans are not full accessibility certification |
| Workflow architecture/contracts | PASS | Ten inactive exports; every HTTP contract exists; dashboard and SVG nodes/edges equal actual JSON; normalization JavaScript executes with local fixtures |
| Existing n8n import upgrade | PASS | Mock API tests preserve the original four IDs, recover known legacy graphs, resolve subworkflow IDs and refuse ambiguous/active graphs before mutations |
| App-only Docker runtime | PASS | Actual Windows app-only Compose service runs on Linux using the offline-built runtime, dummy settings, UID 10001 and forced-off messaging/model flags. API, dashboard, both self-hosted fonts and all nine browser journeys pass; populated named-volume data also survives an app restart with foreign keys intact. Windows routing and standard online build are separate checks |
| Vite preview proxy | PASS | Full inquiry-to-CRM-to-viewing-to-follow-up journey passes through port 3012 to the Docker API; public platform forwarding remains unverified |
| npm dependency audit | PASS | Zero known vulnerabilities; dependency audit is not a penetration-test claim |
| Credential/source scan | PASS | No current runtime credential values, private keys or provider/GitHub token patterns found in 120 candidate source/artifact files. Private settings, state and reports are ignored and excluded from the Docker build |
| Normal online multi-stage Docker build in Cloud | FAIL | Previously failed due to DNS for package hosts inside build containers. Runtime verification uses identical locked host-downloaded wheels and the checked frontend build. This does not prove an unmodified online build on Windows |
| Real Windows PowerShell 5.1, NTFS ACL, Desktop/WSL routing | NOT VERIFIED | Requires the owner's laptop; launcher reports local PASS/FAIL and creates no n8n service |
| Owner's n8n execution/node compatibility | NOT VERIFIED | No Cloud connection to localhost. Import JSON structure and mocked management operations are not runtime execution; manually run local Test Evaluation and fixture modules |
| Official Meta account, webhook registration, template approval, delivery | NOT VERIFIED | Signed fixtures and mocked Graph HTTP calls only. No live credentials/account permissions, public HTTPS callback or test-account delivery checked |
| Live paid model, external channels/calendar | NOT VERIFIED | Disabled/unconnected; deterministic qualification works without a provider. No paid request or customer message sent |
| Multi-client commercial production launch | NOT VERIFIED | No release/publication occurred. Pilot-hardening prerequisites remain below |

## Preservation and safety

Migration 002 creates conversation controls, consent history, idempotent automation receipts and incidents. Existing CRM tables are not rebuilt, dropped or re-keyed. Tests initialize a populated v1 database, apply migration twice and check business row counts and foreign keys. Back up real SQLite data before an upgrade; no owner data has been migrated remotely. The preview/test databases and containers use fictional, isolated state. One existing Cloud API on port 8000 lacked the new operations contracts, so the upgrade was tested with separate owned APIs/containers rather than replacing an unrelated running service. Initial font packaging and dark contrast defects were corrected and the final complete Docker suite passed. Early repeat runs reached the existing demo rate limit; fresh isolated test runtimes completed without weakening it.

The Windows configuration still runs only MADAR, keeps the existing local n8n instance and volume, stores private settings in the ignored ACL-protected folder, and forces external/model flags off. The expanded importer updates inactive managed workflows, binds credentials/subworkflow IDs and refuses activation/deletion. No source export contains secrets. Production workflows have not been published or activated.

## Reproduce

```bash
.venv/bin/python -m pytest -q
npm --prefix frontend run build
# Point at your own running, isolated demo API; the default port is 8000:
MADAR_E2E_BASE_URL=http://localhost:8000 npm --prefix frontend run test:e2e
npm --prefix frontend audit --audit-level=moderate
```

PowerShell tests require `pwsh` or `MADAR_PWSH_PATH`; they report a skip if unavailable. Chromium path is selectable with `MADAR_CHROMIUM_PATH`. The complete browser suite has nine journeys, including a thirteen-page light/dark accessibility pass, keyboard dialog trapping, actual graph selection and WhatsApp inquiry-to-viewing/opt-out/handoff. Preserve the application's rate limits: more than ten demo creations in five minutes against the same API are intentionally rejected. Repeat runs should use isolated fresh test processes/containers or wait.

## Production boundary

This is a functional local operating system and a stronger pilot package, with a luxury interface and production-oriented automation contracts. It still uses one SQLite application process, one provider-tenant binding per deployment and collections capped at 1,000 rows. Distributed durability, per-company encrypted provider credentials, broad pagination, MFA/recovery/SSO, billing, external calendar sync, complete Arabic UI localization, all WhatsApp media/template types, and authorized live-provider acceptance remain work for a wider enterprise SaaS release. The bounded rules assistant is not unrestricted conversational AI.

The platform supplied no public Web Preview forwarding hostname/tool. Local application/preview routes and generated screenshots can be verified; public forwarding remains NOT VERIFIED. See [screenshots](previews/README.md), [workflow contracts](workflow-architecture.md), [WhatsApp setup](whatsapp-setup.md), [Windows startup](windows.md) and [deployment](deployment.md).
