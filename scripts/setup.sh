#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
python3 -m venv .venv
.venv/bin/python -m pip install --cache-dir /tmp/madar-pip-cache -r requirements.lock
npm --prefix frontend ci --cache /tmp/madar-npm-cache --no-audit --no-fund
npm --prefix frontend run build
mkdir -p var
.venv/bin/python -c 'from backend.db import migrate; migrate()'
