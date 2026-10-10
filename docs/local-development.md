# Local Docker development and self-hosted n8n

Run these commands **on your computer**, alongside your existing n8n. Codex Cloud cannot reach your localhost and does not need your local API key. Docker Desktop (or Docker Engine) with Compose v2.24+ and Bash are required.

## One-command setup for an existing Docker n8n

```bash
bash scripts/local-dev.sh
```

The script builds MADAR, prompts for `N8N_API_KEY` with hidden input, writes an ignored `.env` with mode 0600, generates missing local authentication tokens, starts the dashboard, and attaches the single running n8n container publishing port 5678 to the `madar-local` network. It preserves your existing n8n account, volume and encryption key. It verifies workflow read access and the authenticated MADAR bridge, then installs four **inactive** workflows. It never activates workflows, dispatches messages, or enables paid model calls. A scoped n8n key needs workflow read/create/update and credential create permissions; use the narrowest permissions your version supports.

Open **http://localhost:8000** and select **Open interactive demo**. The real workspace is `madar`; the initial email defaults to `admin@madar.local`. The generated administrator password stays in your private `.env`. Do not paste that file into chat. Local demo sessions contain fictional data and are isolated from the real workspace.

If several containers publish 5678, choose the correct one locally and attach it:

```bash
docker network connect --alias n8n madar-local YOUR_N8N_CONTAINER
```

Use one container with the `n8n` alias. Never run the optional Compose n8n service concurrently with your existing instance on port 5678.

## Addresses and native n8n

| Setting / client | Existing Docker n8n | Native n8n process |
| --- | --- | --- |
| Browser / host `N8N_BASE_URL` | `http://localhost:5678` | `http://localhost:5678` |
| MADAR container `N8N_CONTAINER_URL` | `http://n8n:5678` | `http://host.docker.internal:5678` |
| n8n callback `MADAR_N8N_APP_URL` | `http://app:8000` | `http://localhost:8000` |

Container localhost refers to that container, not your computer. The wizard detects the native-process case and adjusts these settings. On Linux, a native n8n bound strictly to `127.0.0.1` may be inaccessible through Docker's host gateway. Keep n8n local; run the Python checks/deployment on the host as below, or use a Docker n8n attached to the shared network. The dashboard's n8n verification requires a working container-to-n8n route. Docker Desktop usually routes `host.docker.internal` to the host. Local HTTP is allowed for loopback, private IPs and explicit Docker names; public hosts require HTTPS. URLs containing credentials, query strings or fragments are rejected.

For native n8n or step-by-step operation, install Python 3.12+ and use the locked helper dependencies (Node is unnecessary for this Docker route):

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.lock
.venv/bin/python -m scripts.local_n8n init --n8n-url http://localhost:5678 --callback-url http://localhost:8000 --container-url http://host.docker.internal:5678
docker compose up -d --build app
.venv/bin/python -m scripts.local_n8n check
.venv/bin/python -m scripts.local_n8n test
.venv/bin/python -m scripts.local_n8n deploy
```

`check` reads one workflow page without modifications. `test` also checks MADAR health and invokes due-follow-up evaluation using `MADAR_BRIDGE_TOKEN`; it can queue internal work but does not call dispatch. It requires development mode with external sends disabled. These commands read `N8N_BASE_URL` and `N8N_API_KEY` from private `.env` (which takes precedence over stale shell bindings); credentials travel in headers. Keys never appear in command arguments, printed output, workflow JSON or deployment manifests. HTTP redirects and environment HTTP proxies are disabled for these local helpers.

The deployment manifest in ignored `var/n8n-deployments/` stores only instance URLs and managed IDs. Keep it to update the same inactive workflows on subsequent runs. Active managed workflows cannot be overwritten. Deleting this manifest can create duplicates; it does not remove workflows or credentials. If tokens change, update the corresponding n8n header credentials securely; deployment preserves existing credentials.

## Import JSON without API deployment

All four files in `workflows/` are importable exports with inactive defaults. Prepare callback addresses without embedding secrets:

```bash
.venv/bin/python -m scripts.local_n8n prepare --callback-url http://localhost:8000
```

Import the files from `var/n8n-import/` in n8n. Create two **Header Auth** credentials there: `MADAR bridge` with header `Authorization: Bearer <MADAR_BRIDGE_TOKEN>`, and `MADAR ingestion` with `Authorization: Bearer <MADAR_INGEST_TOKEN>`. Read these values privately from your local `.env`; never put them in exported JSON. Select those credentials on the HTTP nodes and set the scheduler's error workflow to **MADAR Error Monitor**. The API deployment helper performs this binding automatically.

Execute **MADAR Test Evaluation** manually in your n8n UI. Confirm a successful tick response; this is the real workflow-runtime check Cloud cannot perform for your instance. The error monitor only redacts logs; it is not an external alert service. Activate the scheduler only when you choose to schedule local evaluations. Keep `MADAR_ALLOW_EXTERNAL_SEND=false`; an active scheduler cannot override this gate.

## What each key protects

| Key | Purpose | Secure source |
| --- | --- | --- |
| `N8N_API_KEY` | Grants the local helper/app access to n8n's management API | Create a restricted key in your own n8n settings; enter at the hidden local prompt |
| `MADAR_BRIDGE_TOKEN` | Protects `/api/bridge/tick` and `/api/bridge/dispatch` from unauthenticated scheduler calls | Generated automatically with Python `secrets.token_urlsafe(32)` |
| `MADAR_INGEST_TOKEN` | Protects normalized lead ingestion and binds it to the configured workspace | Generated automatically with the same cryptographic generator |
| `N8N_ENCRYPTION_KEY` | Encrypts credentials for the optional **new** Compose n8n instance | Generated locally; preserve an existing n8n instance's own encryption key |
| `MADAR_AI_API_KEY` | Optional provider key authorizing OpenAI API calls | Create a restricted project key in the OpenAI platform API-key settings; set budgets and store it only in your private server `.env` |

**`MADAR_AI_API_KEY` is not needed for the dashboard, CRM, rules assistant or n8n.** It is a provider credential, not MADAR endpoint authentication or a dashboard password. A random generated string will not work as an OpenAI key; it must be issued by the provider. Optional inference additionally requires `MADAR_ALLOW_MODEL_USAGE=true` and can incur costs. The local Docker configuration keeps it disabled. Never use a `VITE_` variable for any key: those values can enter browser bundles.

To generate another private bridge/ingestion token on your computer:

```bash
python3 -c 'import secrets; print(secrets.token_urlsafe(32))'
```

Store it privately and update the matching n8n credential. `.env`, local state, database files, deployment manifests and screenshots are ignored by Git and excluded from Docker build context. Do not run `docker compose config` without `--quiet` when sharing output: it can expand secrets. Anyone with local Docker administration privileges can inspect container settings.

## Optional new n8n and development preview

For a completely new isolated n8n instance, initialize `.env` first, then use `docker compose --profile automation up -d`. Complete n8n's own local account setup and generate its API key there. The supplied n8n version is configurable through `N8N_IMAGE`; runtime compatibility must be verified on the version you actually run. The optional profile has its own volume and local HTTP cookie settings; it is for local development.

For source development with Python 3.12+ and Node 24:

```bash
bash scripts/setup.sh
npm run dev
```

This starts the API on 8000 and Vite on **3000**, both bound to `0.0.0.0`. Use your platform's Web Preview for port 3000. If its forwarded hostname is blocked by Vite, set the exact hostname in `MADAR_PREVIEW_HOSTS` before startup. The API proxy handles same-origin mutations while retaining cross-origin rejection. No preview hostname or forwarding tool is supplied in this Cloud session, so public preview forwarding cannot be verified here. The backend also serves the production dashboard on 8000.

For Cloud dashboard preview keep `N8N_ENABLED=false`; do not run the local integration scripts there. No tunnel or remotely accessible local n8n is required.

```bash
.venv/bin/python -m pytest -q
npm --prefix frontend run build
npm --prefix frontend run test:e2e
MADAR_E2E_BASE_URL=http://127.0.0.1:3000 npm --prefix frontend run test:e2e
```

The browser suite uses `/usr/bin/chromium` by default; set `MADAR_CHROMIUM_PATH` to your installed executable elsewhere. Provider and n8n API mock tests verify request contracts and guards; they do not prove delivery or workflow execution on your computer.
