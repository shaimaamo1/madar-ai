#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
if [[ ! -x .venv/bin/python || ! -d frontend/node_modules ]]; then
  bash scripts/setup.sh
fi
task_api_pid=""
cleanup() { if [[ -n "$task_api_pid" ]]; then kill "$task_api_pid" 2>/dev/null || true; fi; }
trap cleanup EXIT INT TERM
if ! .venv/bin/python -c "import urllib.request,json; assert json.load(urllib.request.urlopen('http://127.0.0.1:8000/api/health',timeout=2))['service']=='madar-ai'" 2>/dev/null; then
  PORT=8000 bash scripts/start.sh &
  task_api_pid=$!
fi
.venv/bin/python - <<'PY'
import json,time,urllib.request
for attempt in range(20):
    try:
        assert json.load(urllib.request.urlopen('http://127.0.0.1:8000/api/health',timeout=2))['service']=='madar-ai'
        break
    except Exception:
        time.sleep(.5)
else:
    raise SystemExit('MADAR API did not become ready; inspect its startup output.')
PY
# Standard root development command for Web Preview; same-origin API proxy.
npm --prefix frontend run dev -- --port "${PORT:-3000}" --strictPort
