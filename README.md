# MADAR AI

A real estate operations workspace for Egypt and the Gulf, with a React/TypeScript dashboard and a tenant-scoped FastAPI backend.

The working local journey is **website inquiry → bilingual qualification → verified property matching → CRM → viewing booking → follow-up → analytics**. All seeded demo data is fictional. The rules assistant operates without external services; a real language model is optional and not yet authorized here.

## Run on Windows

With Docker Desktop installed and your existing n8n running at `http://localhost:5678`, run from this folder:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\Start-Madar.ps1 -ReplaceApiKey
```

Enter the local key at the hidden prompt. The launcher handles setup/startup, imports inactive workflows without duplicate workflow creation, checks every component, and opens the dashboard. Later starts can omit `-ReplaceApiKey`. No host Python, Node or Bash is needed. See [Windows setup, PASS/FAIL reporting and local checks](docs/windows.md).

## Run locally

For your existing local n8n and Docker development, run **on your computer**:

```bash
bash scripts/local-dev.sh --replace-api-key
```

The hidden API-key prompt writes private ignored settings; four workflows deploy inactive. Open **http://localhost:8000**. See [the local setup guide](docs/local-development.md) for native n8n, networking, JSON import and key explanations. `MADAR_AI_API_KEY` is optional and unnecessary for the rules assistant or n8n.

For source development / Cloud Web Preview, use Python 3.12+ and Node 24:

```bash
bash scripts/setup.sh
npm run dev
```

Use Web Preview on port **3000** (Vite) or the built application on port 8000 and select **Open interactive demo**. Each session receives a private seeded company. Company settings can provision an isolated empty client company. A standalone public website chat is served at `/chat?company=WORKSPACE_SLUG`.

For the initial real workspace, sign in with workspace `madar` and the configured administrator email. In development only, an initial private password is written to `var/initial-admin-password` (0600); it is never committed or logged. Production requires an explicitly injected password, HTTPS, and demo mode disabled. `.env.example` documents configuration names without credentials.

## Verify

```bash
.venv/bin/python -m pytest -q
npm --prefix frontend run build
# Requires the application running and /usr/bin/chromium:
npm --prefix frontend run test:e2e
```

The API contract is available at `/api/docs`. SQLite migration 001 is in `backend/schema.sql`; repeatable initialization runs during startup. Local state is kept in ignored `var/`.

## What is implemented

- Tenant isolation, administrator/agent roles, Argon2 passwords, expiring HttpOnly sessions, password changes, audit records, and cross-site mutation guards.
- Contact deduplication, lead scoring, stage changes, least-loaded active-agent assignment, conversation history, tasks, and recorded deals/loss reasons.
- English/Egyptian Arabic inquiry parsing, customer intent, strict inventory matching, human handoff, and self-service viewing slots with transactional conflict checks.
- Follow-up and reminder evaluation, availability tasks, dormant reactivation/retention queues, opt-outs, and an approval-gated delivery outbox.
- Responsive light/dark dashboard, Arabic navigation and RTL, management metrics/report exports, property comparison, listing-copy drafts, and an editable ROI scenario calculator.
- Official Telegram and Meta webhook/dispatch adapters, Facebook Lead Ads fetch, message status updates, approved parameter-free WhatsApp template support, and normalized email/CRM ingestion.
- Four modular inactive n8n workflows and a direct API deployment tool; Docker preparation, backup helper, client customization guide, sales presentation, pricing assumptions, and portfolio draft.

## External access and current limits

The local website journey is functional. Live **your local n8n, WhatsApp, Telegram, Facebook/Instagram, email/CRM accounts, and model access remain unverified**. Codex Cloud cannot reach your computer; local scripts perform the required checks without sending credentials to Cloud. No external messages, production deployment, public content, or purchases have been performed.

This release uses one process and SQLite with persistent storage; it is suitable for evaluation and a hardened low-volume pilot. It is not a completed production SaaS launch. Each deployment binds one external-integration tenant; multiple CRM companies are isolated, but per-tenant channel credential storage, large-client pagination, MFA/recovery/SSO, billing, and external calendar synchronization require further work. Some operational UI labels remain English. Provider node compatibility and test-account delivery must be verified after authorization.

## Documentation

- [Windows one-command deployment](docs/windows.md)
- [Local Docker, n8n, secrets and preview](docs/local-development.md)
- [Architecture](docs/architecture.md)
- [Integration access and official providers](docs/integrations.md)
- [Deployment and operations](docs/deployment.md)
- [Client customization](docs/client-customization.md)
- [Commercial pack and demo script](docs/commercial.md)
- [Verification evidence and remaining work](docs/status.md)

Credentials belong in secure environment settings, never source control or chat. Real-customer messaging, production release, public publication, paid services, and production-data deletion require the owner’s explicit approval.
