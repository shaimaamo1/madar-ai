#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
task_env_args=()
if [[ -f .env ]]; then task_env_args=(--env-file .env); fi
exec .venv/bin/python -m uvicorn backend.main:app --host 0.0.0.0 --port "${PORT:-8000}" --no-access-log "${task_env_args[@]}"
