# Development and deployment

## Current cloud development environment

Run `bash scripts/setup.sh` from the checkout. It uses Python 3.12+, Node 24, frozen Python dependencies, `npm ci`, a TypeScript check, and a Vite build. Start source development / Web Preview with `npm run dev` on port 3000, or serve the production build with `bash scripts/start.sh` on port 8000. The API serves the built frontend from the same origin, and `/api/health` verifies database access. The root development command starts Vite with a same-origin API proxy to port 8000. Set exact forwarded preview hosts through `MADAR_PREVIEW_HOSTS` if needed. See [local Docker and n8n](local-development.md). Use the existing isolated checkout; no Git worktree is needed.

Local demonstration login creates a private seeded company with fictional data. The real `madar` administrator uses `admin@madar.local` unless configured otherwise. An initial local password is generated into `var/initial-admin-password` with mode 0600; it is never logged. `.env.example` contains variable names and non-secret defaults only. Uvicorn can load a local `.env` file using `--env-file .env`; settings supplied by the host are preferred. Never commit credentials.

Tests: `.venv/bin/python -m pytest -q`; `npm --prefix frontend run build`; and, with the API running, `npm --prefix frontend run test:e2e`. Browser tests use the cloud’s `/usr/bin/chromium`. Adjust the Playwright executable setting or install its supported browser on other systems. Test outputs and local state are ignored by Git.

## Prepared production package

`Dockerfile` uses a Node build stage and a non-root Python runtime. `docker-compose.yml` keeps the database in a named volume, binds the app to loopback, and leaves real sends disabled. Container build/runtime verification evidence is recorded in [status](status.md). Node/Python base-image tags should be pinned by digest in a production release. No paid hosting or production deployment has been activated.

For a low-volume pilot, use one Linux application process, persistent SQLite disk, and a managed HTTPS reverse proxy. Securely inject `MADAR_ENV=production`, `MADAR_DEMO_MODE=false`, the approved HTTPS `MADAR_PUBLIC_URL`, an initial administrator password of at least 12 characters, and an owner email. Startup refuses unsafe production defaults. An ephemeral serverless disk is unsuitable for this SQLite release. Begin with one client pilot; move to PostgreSQL before multiple replicas or large ingestion volume.

Supply integration credentials through the host’s encrypted secret storage. Never use proxy placeholders for secrets verified locally (passwords, webhook signatures, bridge tokens). The supplied initial password applies only to a fresh database; existing accounts change passwords through the authenticated account endpoint and dashboard. Never reinitialize or delete a production volume to change access.

Before production approval: exercise the provider test accounts, backup/restore, recipient consent, response policy, tenant-access tests, resource limits, monitoring, and accessibility review. This implementation does not yet provide MFA, self-service password recovery, enterprise SSO, encrypted database storage, consent-evidence retention, a billing system, or database-backed distributed throttling. These are specific pilot-hardening tasks, not claims of completed compliance.

## Backup and operations

Use SQLite’s backup API rather than copying a live WAL database. `scripts/backup.py` writes a consistent snapshot to a specified directory and supports a non-destructive restore verification into a separate temporary database. Backups contain personal data; store them encrypted with access limited to the operator and a defined retention period. The production owner must approve deletion or restoration that replaces live data.

n8n is the primary production scheduler. Activate only approved workflows with a restricted bridge token. The optional local worker is a development fallback; do not run both scheduler implementations concurrently. Logs avoid provider URLs and credentials; CRM activities remain tenant-scoped. Add centralized monitoring and an alert route before unattended production operation.

Publication of this Codex development environment is separate from app deployment. The environment draft’s installation and startup instructions have been saved for review. Review/save them in environment settings and publish the environment if you want a reusable snapshot. A saved draft alone neither runs scripts nor deploys the product.
