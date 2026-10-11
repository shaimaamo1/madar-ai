# Enterprise orchestration verification — 11 October 2026

This release supersedes the ten-export / 44-node milestone in [bilingual-verification.md](bilingual-verification.md). Customer records, private configuration, existing volumes and the Windows ACL/Compose fixes are preserved. Migration 003 adds tables and indexes without rewriting business records.

## What is implemented

Eight business workflows now contain **297 connected executable nodes**; six support/demo modules bring the total to **14 exports / 327 executable nodes**. Sticky notes are excluded. Every executable node is reachable. Calculations produce durable business evidence; validation and HTTP error branches record scoped incidents and stop rejected operations. CRM intake, consent, booking/resource conflicts and queue creation remain authoritative backend transactions.

| Business workflow | Executable nodes | Purpose |
| --- | ---: | --- |
| Omnichannel Intake | 41 | Authenticated normalization, contact collision prevention, language/consent/injection signals, workload and atomic intake |
| Lead Intelligence | 36 | Preference completeness, scoring evidence, urgency/viewing intent, assignment/ownership and readiness |
| Property Matching Engine | 36 | Availability, intent/budget/area/category/rooms/size funnel, amenities, grounded matches and explicitly nonmatching alternatives |
| Viewing Reservations | 36 | Explicit request, customer/property/adviser validation, timezone, overlapping resources and atomic booking |
| Follow-up Scheduler | 38 | Due tasks, consent/opt-out/human suppression, availability, reminders, retention/reactivation and stable queue keys |
| WhatsApp Conversation | 36 | Recent context, Arabic/English, Meta window/template policy, verified inventory, grounded draft and review |
| Human Handoff & Escalation | 36 | Priority, adviser workload/owner, response SLA, persistent case, acknowledgement/resolution policy and automation pause |
| Sales Reporting | 38 | Channel/pipeline/adviser conversion, actual commissions/sales/open opportunities, viewing and follow-up backlog |

The other six exports are Full Demo (11), Delivery Reconciliation (5), WhatsApp Delivery (5), Error Monitor (3), Ingestion Subworkflow (3), Test Evaluation (3). The canvases use four colored evidence phases with connected success/rejection paths. Dashboard diagrams have zoom/fit controls; [SVG diagrams](diagrams/) are generated from the exact exports.

## Verification boundaries

See [n8n-runtime-acceptance.json](n8n-runtime-acceptance.json) for actual isolated n8n evidence and workflow SHA-256 fingerprints. The developer acceptance tool uses **n8n 1.113.3 in a disposable Linux/Cloud Docker fixture**, fictional users/data, temporary credentials, no mounted customer volumes, no activation and no provider calls. It automatically imports/reimports through the actual public API, executes inactive workflows with the official CLI, reads actual successful execution evidence, rejects duplicate booking and records an actual failed cross-tenant-reference attempt. This verifies the fixture version; it does **not** verify the owner's Windows laptop or existing n8n installation/version.

| Component | Result | Evidence / limitation |
| --- | --- | --- |
| Eight graphs ≥30 connected nodes | PASS | Source validation and actual successful full-demo execution |
| Actual n8n API import/reimport | PASS | Fourteen inactive IDs preserved in isolated fixture |
| Actual full-demo orchestration | PASS | Eight persisted business outcomes; parent n8n success checked against the exact run ID |
| Explicit incident/error routing | PASS | Generated qualification module rejects unrelated customer; dashboard incident recorded |
| Backend / migration / isolation / replay / conflict / Windows helper regression tests | PASS | 110 passed; 1 native Windows ACL test skipped (Linux PowerShell Core helper tests included) |
| Frontend unit tests / build | PASS | 4 passed; matching catalogs, source coverage, formatting, identities and TypeScript build |
| Browser journeys and accessibility | PASS | 15 passed in production Chromium; both languages, fourteen pages, light/dark/mobile, forms, booking, demo truthfulness and agents |
| Credentials / external messaging boundary | PASS | Fictional acceptance credentials, no provider sends, no workflow activation; secret scan before commit |
| Windows PowerShell 5.1 / Desktop / native ACL execution | NOT VERIFIED | Linux PowerShell Core regression execution is not Windows verification |
| Owner's existing local n8n | NOT VERIFIED | Cloud never connects to the laptop's localhost |
| Official Meta delivery / paid language models | NOT VERIFIED | No real customer message or paid provider request authorized or made |

The fixture's automatic Error Workflow is **not** claimed verified for manual/CLI execution: n8n deliberately skips it in that mode. Business modules therefore record failures explicitly before throwing. Scheduled/production failures also retain the existing importer-bound Error Monitor, whose live scheduling requires separate authorization.

## Demo and AI truthfulness

System Health checks authenticated backend access, SQLite integrity, messaging safety, adviser SLA and actual configured n8n API read access. Docker Desktop and Windows remain NOT VERIFIED until tested there; the web server does not infer their state. Run Full Demo queues an isolated fictional run, displays persisted step references and offers verification. It never substitutes a browser simulation for n8n execution.

A short-lived capability binds one run, tenant, event and server-controlled scenario. Arbitrary contact/booking input and unrelated customer references are rejected. Steps execute in order with stable receipts; failures revoke capability and mark Failed; expired runs can be queued again. Reset remains an explicit action scoped to the signed-in fictional tenant. Customer workflows retain no execution payloads. **Only Full Demo retains successful fictional execution evidence**, because n8n otherwise deletes the execution reference. Its capability is revoked before successful completion; error payload retention remains disabled.

Five agents expose qualification, intent detection, inventory explanations, bilingual draft generation and sales assistance. Recorded scoring, facts, explanations and drafts use deterministic rules/templates. Optional structured intent interpretation and the existing preference extractor can use OpenAI only with configured credentials and `MADAR_ALLOW_MODEL_USAGE=true`; fictional tenants always suppress paid use. Modes and provider usage are reported truthfully. No model invents listing facts, grants consent, reserves appointments or sends a draft. Paid inference has not been verified live.

## Running locally

On Windows, keep the existing n8n at `http://localhost:5678`. From the repository run `powershell -NoProfile -ExecutionPolicy Bypass -File .\Update-Madar.ps1` (or double-click Update-Madar.cmd). The existing updater backs up, fast-forwards, rebuilds and launches MADAR; it does not create another n8n instance. Start-Madar.cmd / Start-Madar.ps1 remain available when no Git update is needed. Secure local settings and repeat-import IDs are preserved.

Open a fictional dashboard demo, go to **System Health → Queue full demo**, then **Execute Workflow** on the imported inactive **MADAR Full Demo** in the existing n8n editor. Return and select **Verify n8n execution**. This local execution action is necessary: the supported n8n public API has no arbitrary workflow-run endpoint, and this release deliberately does not activate workflows or use private authenticated editor endpoints. No PowerShell troubleshooting was required during development.

Optional developer reproduction on an isolated Linux/Cloud Docker machine with the cached image:

```bash
DOCKER_CONFIG=/tmp/madar-docker-config .venv/bin/python -m scripts.n8n_acceptance --isolated-fixture --output /tmp/madar-n8n-report.json
```

`--screenshots` additionally uses the development Chromium/Playwright installation to capture actual verified-demo and n8n-editor previews. These developer dependencies are not introduced into Windows startup.

Final release checks: production build passed; npm production dependency audit reported 0 vulnerabilities; 140 repository text files scanned with no credential-pattern/environment-secret matches and no tracked private configuration. Four additional Chromium checks on the Vite preview verify final Arabic/English light/dark/mobile/health styling and the proxy after presentation polish. The preview is served on port 3013 with a fictional, provider-disabled API fixture.
