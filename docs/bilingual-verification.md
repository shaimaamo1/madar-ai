> Historical bilingual milestone. Current orchestration inventory and actual runtime acceptance are documented in [enterprise-verification.md](enterprise-verification.md).

# Bilingual and Windows milestone verification

Updated 11 October 2026. This is evidence for completed milestones, not acceptance of the full new enterprise automation brief.

| Check | Result | Actual evidence / limits |
| --- | --- | --- |
| Backend/API/integration regression suite | PASS | **99 passed, 1 skipped**. The skipped check requires native Windows ACLs. Includes real local-Git update fixtures, existing CRM/tenant/migration/conflict/consent/outbox tests, public timezone allowlist and actual workflow reachability/source-quality checks |
| Frontend unit suite | PASS | **4 passed**: 760 matching catalog entries, placeholders/Arabic text, source coverage/canonical control identity, all actual workflow labels and locale formatting |
| TypeScript / production frontend | PASS | `tsc --noEmit` and Vite build; no new runtime dependency; licensed fonts bundled |
| Complete production browser suite | PASS | **14 passed** against the final built frontend served by an isolated FastAPI process on loopback port 18113. Real fictional API journeys; external messaging, n8n and paid models disabled |
| Complete Arabic page audit | PASS | All thirteen pages checked for translated navigation/status/form labels, RTL, locale fonts/numerals, desktop/mobile document overflow and automated axe WCAG A/AA checks; all ten actual workflow diagrams have Arabic node/group labels |
| Existing English / premium behavior | PASS | Original nine journeys retained: CRM, property creation/comparison/settings, public booking, follow-up, dark/mobile, font delivery, all-page English light/dark accessibility, dialog trapping and sandbox handoff/opt-out |
| Instant switching and persistence | PASS | DOM controls retain identity, inputs/selections/checkboxes/search/comparison/unsent messages survive, canonical values persist through the API, reload/new tab restores language, known errors and browser validation retranslate |
| Safe Windows update logic | PASS | Eight isolated real-Git scenarios on Linux PowerShell Core: success, already-current, wrong branch, tracked/untracked edits, divergence, fetch failure, backup failure. Docker/Windows discovery and ACLs simulated; verifies recovery requests/artifacts and unchanged dummy environment bytes |
| Batch wrapper / Windows syntax | PASS | Source checks retain launcher exit status and invoke existing PowerShell entry points; PowerShell source parses/executes in the applicable Linux tests. Does not prove native double-click execution |
| Source workflow report | PASS | Ten inactive exports, **44 functional/reachable nodes**, **35 connections**. Repository type/version matrix, branch targets, reachability and inactive/log retention checks pass; malformed/disconnected fixtures fail |
| 30–60-node major workflows | FAIL / unfinished | Requested complexity targets have not been implemented. No filler nodes or source workflow rewrites were added. [Inventory and exact continuation](enterprise-continuation.md) |
| Run Full Demo / System Health / complete AI agent suite | NOT TESTED / unfinished | Not implemented in this milestone. Existing UI sandbox business journeys and optional quoted-preference model adapter are not a substitute for actual n8n execution |
| npm dependency audit | PASS | Zero known vulnerabilities in the existing dependency set |
| Credential/source scan | PASS | Tracked/untracked non-ignored source/artifact text scanned against available runtime secret values and credential/private-key patterns: zero findings. Private settings, data and deployment state remain ignored |
| Existing Windows security / workflows / data | PASS for source preservation | `Madar.Local.ps1`, workflow exports, importer identities and database migrations unchanged; no owner/local-volume/customer data was accessed or changed |
| Windows PowerShell 5.1 / NTFS ACL / Desktop / batch browser associations | NOT TESTED | Requires the Windows laptop. Linux PowerShell/Core and fake OS tests do not establish these checks |
| Existing local n8n import / execution / installed node compatibility | NOT TESTED | No Cloud connection to owner localhost. Mock import tests and valid JSON do not establish runtime success |
| Live Meta/WhatsApp / paid model / external messaging | NOT TESTED | No real delivery, paid inference, workflow activation or account authorization used |
| Final enterprise demo / production release | NOT TESTED | Expanded brief still requires the documented architecture and runtime milestones; no production publication occurred |

The earlier Docker online-build limitation remains recorded in [premium verification](premium-verification.md). This milestone verifies the production application directly on Linux; it does not claim a new Docker Desktop build/run or Windows acceptance.

## Reproduce

```bash
MADAR_PWSH_PATH=/path/to/pwsh .venv/bin/python -m pytest -q
npm --prefix frontend run test:unit
npm --prefix frontend run build
# Use your own fresh, isolated fictional API serving the built frontend:
MADAR_E2E_BASE_URL=http://localhost:8000 npm --prefix frontend run test:e2e
npm --prefix frontend audit --audit-level=moderate
.venv/bin/python -m scripts.workflow_quality
```

PowerShell and Chromium executables are selectable with `MADAR_PWSH_PATH` and `MADAR_CHROMIUM_PATH`. If PowerShell is unavailable its tests explicitly skip. Preserve the existing demo-creation rate limit when repeating browser runs.

## Minimum local action

Keep the existing n8n running and double-click **Start-Madar.cmd**. Enter a missing API key only at the hidden prompt. The launcher imports/updates inactive managed workflows and opens the checked dashboard. Subsequently double-click **Update-Madar.cmd** on a clean expected-branch checkout. Check their reports on Windows; execute **MADAR Test Evaluation** in the existing n8n UI to verify the current installed workflow/credentials/callback route. That evaluation only checks queue/status contracts, not the unfinished full automation demo.

No secret needs to be shared in chat. Leave real delivery and paid model usage disabled. See [Windows instructions](windows.md), [localization implementation](localization.md), [workflow report](workflow-quality.json) and [enterprise continuation](enterprise-continuation.md).
