# Windows: one launcher for MADAR and your existing n8n

Requires Windows PowerShell 5.1+ and Docker Desktop with **Linux containers** and Compose 2.24.4+. Your existing n8n must already run at `http://localhost:5678`. Python, Node and Bash are not required on Windows. Use a local NTFS/ReFS folder, not a network share. The first build needs Internet access to Docker, npm and Python package registries.

From the project folder, run:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\Start-Madar.ps1 -ReplaceApiKey
```

Enter your new local n8n API key at the hidden prompt. The script starts Docker Desktop if its daemon is stopped, checks dependencies and ports, builds and starts MADAR, verifies API/database and dashboard files, imports the workflows, saves a PASS/FAIL report, and opens the dashboard. Execution policy applies only to this PowerShell process; system policy is not changed. No administrator shell is required. It does not install Docker Desktop or change Windows/WSL/firewall settings.

For later starts, omit `-ReplaceApiKey` to reuse the saved key:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\Start-Madar.ps1
```

`Setup-Madar.ps1` performs the same setup and startup without opening the browser. `Start-Madar.ps1 -NoBrowser` does likewise. You can select **Open interactive demo** once the dashboard opens. The real default workspace is `madar`; a fresh database uses the generated initial administrator password in your private settings. Existing accounts/passwords and company data are preserved.

## What happens automatically

- The launcher checks a **local Docker Desktop context**, Linux-container mode, Compose version, and your existing n8n listener. It refuses remote Docker contexts/overrides before requesting a key.
- Dashboard port 8000 is preferred; occupied unrelated ports are never stopped. A free port up to 8010 is selected and callback URLs are adjusted. The existing MADAR app port is reused when possible.
- Docker builds the backend and React dashboard. Both run in one non-root app container and share one browser URL. No separate Vite process is needed for this local deployment.
- The Windows Compose file contains **only `app`**. No duplicate n8n container/account/volume is created. Existing Docker n8n is attached to `madar-local`; native Windows n8n is reached through `host.docker.internal`. Existing n8n credentials and encryption settings are not changed.
- Runtime external-send and paid-model flags are forced off, including when legacy settings enabled them. Startup does not activate workflows or call the dispatch endpoint.
- All 16 requested checks receive PASS/FAIL rows on screen. Non-secret results are saved to ignored `var/windows-setup-report.json`; the process exits with code 1 if a required check fails. If n8n access fails but the dashboard is healthy, the dashboard still opens and the failed n8n checks remain visible.

## Private credentials

The key is collected using `Read-Host -AsSecureString`, passed to the local Docker helper **only through stdin**, and stored in `.madar-local/.env`. The folder and files have Windows ACLs restricted to the current account and SYSTEM. Credentials are plaintext inside this private local settings file because Compose must read them; they are not stored in Git, image layers, command arguments, browser bundles, reports or printed output. Docker administrators can inspect container environment variables.

If a legacy root `.env` exists, the launcher restricts its ACL and copies it into the private folder once, preserving passwords and bridge/ingestion tokens. A replacement API key removes the old key entry. Other secrets remain unchanged. Existing production settings are refused rather than converted. The original root `.env` remains private and ignored; the Windows launcher uses the private copy thereafter.

`.madar-local/`, `.env`, `var/`, and generated output are ignored by Git and excluded from Docker's build context. Do not share either private `.env`, Docker inspection output, or expanded Compose configuration. The launcher uses `docker compose config --quiet` only.

`MADAR_AI_API_KEY` is optional; the rules assistant, CRM, dashboard and n8n operate without it. It authorizes OpenAI provider calls, not MADAR endpoint or dashboard access. If you later authorize paid inference, create a restricted project key in the provider's API-key settings, set a budget, and store it only in your private server settings. A random locally generated string cannot replace a provider-issued key. The Windows launcher keeps model inference disabled. Bridge/ingestion tokens authenticate MADAR integration endpoints and are generated cryptographically when missing.

## Workflow import and local verification

The key needs n8n workflow read/create/update and credential-create access. Ten callback-adjusted, secret-free importable files are also prepared in `var/n8n-import/`; source exports are in `workflows/`.

The upgraded launcher imports ten modules and automatically binds their subworkflow reference. It preserves recognized legacy identities for the original four workflows. See [module architecture](workflow-architecture.md) and [WhatsApp studio](whatsapp-setup.md).

Import preflights n8n's paginated workflow list. Normal repeat starts update the IDs recorded in `var/n8n-deployments/`. If that manifest is missing, matching MADAR workflow names and node identities are recognized and reused. Ambiguous duplicate names, unrelated same-name workflows, mismatched IDs, and active workflows cause a FAIL before workflow mutations; nothing is silently deleted or activated. Preserve the manifest. Losing it may create replacement Header Auth credentials, but existing managed workflows are reused rather than duplicated. Manual same-name imports must be resolved by you; the launcher never deletes them.

The automated local checks verify n8n API read access and MADAR's authenticated bridge. They do **not** execute a workflow in n8n. After successful startup, manually execute **MADAR Test Evaluation** in your existing n8n UI. That confirms the installed node versions, credential bindings and callback route. Enable the scheduler locally only when you choose to run scheduled evaluations; real delivery remains disabled.

## If a component fails

| Report component | Minimum local action |
| --- | --- |
| Docker dependencies / Desktop | Install or update Docker Desktop, enable Linux containers, finish any first-run prompts, and rerun |
| Private configuration | Use a writable local NTFS/ReFS folder and development settings |
| Existing n8n port | Start your existing n8n at Windows localhost:5678; avoid multiple containers publishing that port |
| Docker build | Check Docker resources and registry/package Internet access, then rerun |
| Dashboard port | Free one port from 8000-8010; the launcher does not terminate unrelated applications |
| n8n API and bridge | Re-enter the key with `-ReplaceApiKey`, check scopes, and verify Docker Desktop can reach the native n8n process through `host.docker.internal` |
| Workflow import | Check API scopes, deactivate managed workflows before updating, or resolve ambiguous manual imports |
| Dashboard browser | Open the URL printed in the report manually |

If n8n runs inside WSL rather than directly on Windows, its port must be reachable from both Windows localhost and Docker Desktop. The launcher reports a failed route; it does not change n8n's listen address, publish its API to the Internet, create a tunnel, or modify firewall rules. Use the report's local networking action if needed.

To stop **only MADAR**, preserving all data and your existing n8n:

```powershell
docker compose --project-name madar-ai --env-file .\.madar-local\.env -f .\docker-compose.windows.yml stop app
```

## Tested here versus on your laptop

The Linux Cloud environment runs the Python/API suite, workflow import recovery mocks, browser journeys, Docker runtime checks, PowerShell parsing, and eleven full PowerShell orchestration scenarios using fake Windows/Docker/HTTP operations. The actual PowerShell native-process stdin transfer and local HTTP check are also exercised. The Windows Compose app configuration passed all nine browser journeys using an offline-built runtime and isolated dummy settings with n8n disabled. The official PowerShell Core package used for testing was downloaded over verified TLS and checked against its official SHA256 metadata.

**Real Windows PowerShell 5.1 execution, NTFS ACL enforcement, Docker Desktop/WSL routing, your local n8n API permissions and workflow execution remain local checks.** Cloud cannot reach your laptop, and no attempt was made. Existing Cloud build DNS limitations are recorded in [verification](premium-verification.md); the standard multi-stage build must complete on your laptop. Actual external provider accounts/delivery remain unverified and disabled. Real messaging, billable model use and production deployment require separate authorization.
