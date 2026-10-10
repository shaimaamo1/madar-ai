# Enterprise implementation milestones and continuation

Updated 11 October 2026. This is a candid implementation/dependency map for the expanded enterprise brief. **The full enterprise brief is not complete and the 30–60-node workflow goal is not met.** The current milestone completes interface localization, provides safe double-click Windows launch/update entry points, and audits the real exported graphs. It preserves the existing backend, customer data model, inactive workflow JSON, credentials, volumes and import identities.

## Actual workflow inventory

Sticky notes are excluded. Connected counts mean reachable from a real trigger, not runtime success. Source validation checks the repository's pinned node/version matrix, targets, branches, reachability and safe inactive/logging defaults. It does not establish compatibility with the owner's installed n8n version.

| Actual export | Functional nodes | Connected nodes | Connections | Current complexity target |
| --- | ---: | ---: | ---: | --- |
| MADAR Omnichannel Intake | 6 | 6 | 6 | Not met: 45–60 requested |
| MADAR Lead Intelligence | 6 | 6 | 5 | Not met: 40–55 requested |
| MADAR Viewing Reservations | 4 | 4 | 3 | Not met: 35–50 requested |
| MADAR Follow-up Scheduler | 6 | 6 | 5 | Not met: 35–50 requested |
| MADAR WhatsApp Delivery | 5 | 5 | 4 | Delivery module; full conversation workflow remains to implement |
| MADAR Sales Reporting | 3 | 3 | 2 | Not met: 30–45 requested |
| MADAR Delivery Reconciliation | 5 | 5 | 4 | Dedicated support module |
| MADAR Error Monitor | 3 | 3 | 2 | Dedicated error module |
| MADAR Ingestion Subworkflow | 3 | 3 | 2 | Reusable atomic intake module |
| MADAR Test Evaluation | 3 | 3 | 2 | Safe queue/status check; does not run the complete journey |
| **Total** | **44** | **44** | **35** | **Ten exports; no padding added** |

The requested standalone Property Matching Engine and Human Handoff & Escalation workflows do not exist yet. Their current behavior is implemented inside tenant-scoped backend transactions and the Lead Intelligence contract. [Existing SVG diagrams](workflow-architecture.md) represent these actual exports; localization translates their dashboard labels without changing source identities.

The [machine-readable report](workflow-quality.json) marks live import, installed-node compatibility and actual execution **NOT TESTED**. Reproduce source inspection with `python -m scripts.workflow_quality`; it never connects to n8n. Import tests use mock APIs and prove repeat-import ID handling, not successful execution.

## Why the graphs were not padded

CRM deduplication, qualification/scoring, assignment, history, consent, inventory filtering and outbox creation currently commit atomically in MADAR. Splitting that write into many HTTP nodes would break its consistency and replay guarantees. Property/resource conflicts likewise need the existing database transaction, not a check-then-create race across n8n nodes. Forty transformations on the same envelope would add no business capability.

Meaningful larger canvases require additional implemented capabilities: distinct authenticated channel adapters, validated/enriched preferences with provenance, urgency/readiness/confidence, inventory alternatives and recommendation history, business-hour response-aware follow-up, SLA/acknowledgment/resolution handling, and durable reporting/execution evidence. The next milestone should implement those contracts before drawing corresponding nodes. If the resulting business flow still cannot justify thirty nodes, document that exception instead of inventing processing steps.

## Exact continuation sequence

1. **Audit and define safe orchestration contracts.** Preserve the ten export names/node identities and lost-manifest recovery signatures before graph expansion. Add versioned graph identity recognition to the importer/tests. Keep raw Meta signature verification in the backend; never bypass it with an unsigned n8n webhook. Document request/response schemas, tenant binding, idempotency/event IDs and error behavior.
2. **Build durable isolated demo and health contracts.** The existing single integration-tenant binding cannot safely run dashboard demo tenants through n8n. Add an additive migration for tenant-bound demo runs/steps/execution references and short-lived scoped demo capabilities. Reject non-demo targets; reset only the selected fictional tenant/run. Build authenticated System Health with actual check timestamps, configuration versus access versus execution distinctions, and redacted errors. Docker can be reported only from trusted local evidence, not invented by the web app.
3. **Implement and test AI capability contracts.** The current optional OpenAI adapter extracts quoted preferences with confidence/output validation and deterministic fallback; it does not provide all five requested AI agents. Extend validated intent, urgency/readiness, explanation and reply drafting with provenance, prompt-injection boundaries, timeouts/bounded retries, provider mode/usage reporting and human review. Keep model usage disabled unless separately authorized. Do not let generated listing facts, bookings or unapproved sends bypass backend validation.
4. **Implement inventory, handoff and appointment depth.** Add recommendation history, hard/soft constraint explanations, verified alternatives/no-match handling, tenant-scoped workload/availability, acknowledgment/SLA/resolution, reassignment and no-show outcomes with additive migrations and real tests. Preserve authoritative conflict-safe booking and idempotency.
5. **Expand the eight business canvases.** Connect only implemented contracts and useful n8n branches. Add authentic adapters, success/fallback/error routes, clean horizontal colored groups and reusable modules. Recompute actual reachable counts and generate diagrams from JSON. Keep exports inactive, credentials symbolic, execution payload retention off and external sends disabled. Test Code nodes, expressions and contract mocks; validate installed nodes through local n8n execution separately.
6. **Implement Run Full Demo / Reset Demo Data.** Reuse the safe isolated run contracts; trigger actual n8n paths and display progress, results, truthful AI modes and real execution IDs. Fail visibly if n8n is absent rather than substituting a fake successful execution. Synchronize real fictional CRM, recommendations, drafts, follow-ups, booking, handoff and analytics outcomes. Existing provider-free browser journeys already verify much of the backend scenario, but are not n8n runs.
7. **Local runtime acceptance and presentation assets.** Run import/re-import and full successful/error/replay/conflict journeys on an isolated local fixture with the existing n8n. Record genuine execution references and canvas screenshots. Recheck both languages, mobile/dark/accessibility, migration preservation, launcher/update and secret scans. Produce technical/business scripts and a 60–90-second storyboard tied to verified outcomes; make no invented savings/conversion claims.

Dependency order: scoped demo/health and identity migration → AI/inventory/SLA contracts → major workflow graphs → real demo orchestration → installed n8n acceptance/screenshots → release readiness report. Commit/push each coherent tested milestone to `codex/self-hosted-n8n`.

## Access and authorization still needed

No Cloud request has been made to the owner's `localhost:5678`. The local launcher imports inactive workflows into the existing instance using its privately entered key. Actual Windows PowerShell 5.1/ACL/Desktop and actual n8n execution require the laptop. No new n8n instance, tunnel or remote connection is needed.

Official Meta access, approved templates/public callback and actual paid model use still need credentials/configuration and explicit authorization. No real customer message, workflow activation, production publication or paid request has occurred. The final enterprise demo cannot be declared ready until its actual execution and missing capabilities above are implemented and verified.
