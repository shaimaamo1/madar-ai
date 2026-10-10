#!/usr/bin/env bash
# Run only on your computer. Uses your existing n8n; never creates its account.
set -euo pipefail
cd "$(dirname "$0")/.."
task_init_args=(init)
if [[ ${1:-} == --replace-api-key ]]; then task_init_args+=(--replace-api-key); shift; fi
if [[ $# -gt 0 ]]; then echo 'Usage: bash scripts/local-dev.sh [--replace-api-key]' >&2; exit 2; fi
task_compose=(docker compose -f docker-compose.yml)
task_candidates=()
task_candidate_count=0
while IFS="|" read -r task_image task_container; do
  if [[ "$task_image" == *n8n* && -n "$task_container" ]]; then
    task_candidates+=("$task_container")
    task_candidate_count=$((task_candidate_count + 1))
  fi
done < <(docker ps --filter publish=5678 --format '{{.Image}}|{{.Names}}')
if [[ $task_candidate_count -gt 1 ]]; then
  echo 'Multiple n8n containers publish port 5678; leave only the intended instance on that port before retrying.' >&2
  exit 1
fi
task_n8n_url=http://n8n:5678
task_callback_url=http://app:8000
task_test_app_url=http://app:8000
if [[ $task_candidate_count -eq 0 ]]; then
  task_callback_url=http://localhost:8000
  task_n8n_url=http://host.docker.internal:5678
  if [[ $(uname -s) == Linux ]]; then
    # Native Linux loopback is reachable with host networking; no public n8n port.
    task_compose+=(-f docker-compose.host.yml)
    task_n8n_url=http://localhost:5678
    task_test_app_url=http://localhost:8000
  fi
fi
"${task_compose[@]}" build app
# Hidden prompt writes the ignored host .env with permissions 0600.
"${task_compose[@]}" run --rm --no-deps --interactive --tty \
  --user "$(id -u):$(id -g)" --volume "$PWD:/workspace" --workdir /workspace \
  --entrypoint python app -m scripts.local_n8n "${task_init_args[@]}" --n8n-url http://localhost:5678 \
  --container-url "$task_n8n_url" --callback-url "$task_callback_url"
"${task_compose[@]}" up -d app
if [[ $task_candidate_count -eq 1 ]]; then
  task_container="${task_candidates[0]}"
  task_aliases=$(docker inspect --format '{{with index .NetworkSettings.Networks "madar-local"}}{{json .Aliases}}{{end}}' "$task_container")
  if [[ -z "$task_aliases" ]]; then
    docker network connect --alias n8n madar-local "$task_container"
  elif [[ "$task_aliases" != *'"n8n"'* ]]; then
    # Keep the existing network intact; use its private IP when the alias is absent.
    task_address=$(docker inspect --format '{{with index .NetworkSettings.Networks "madar-local"}}{{.IPAddress}}{{end}}' "$task_container")
    task_n8n_url="http://$task_address:5678"
    "${task_compose[@]}" run --rm --no-deps --user "$(id -u):$(id -g)" \
      --volume "$PWD:/workspace" --workdir /workspace --entrypoint python app \
      -m scripts.local_n8n init --container-url "$task_n8n_url"
    "${task_compose[@]}" up -d app
  fi
fi
"${task_compose[@]}" exec -T app python - <<'PY'
import json, time, urllib.request
for attempt in range(40):
    try:
        data = json.load(urllib.request.urlopen('http://127.0.0.1:8000/api/health', timeout=2))
        if data.get('service') == 'madar-ai':
            break
    except (OSError, ValueError):
        pass
    time.sleep(.5)
else:
    raise SystemExit('MADAR did not become ready; inspect Docker app logs locally.')
PY
task_helper=("${task_compose[@]}" run --rm --no-deps --volume "$PWD:/workspace" --workdir /workspace
  --user "$(id -u):$(id -g)" --entrypoint python)
"${task_helper[@]}" app -m scripts.local_n8n prepare
"${task_helper[@]}" -e "MADAR_TEST_APP_URL=$task_test_app_url" app \
  -m scripts.local_n8n test --n8n-url "$task_n8n_url"
"${task_helper[@]}" app -m scripts.local_n8n deploy --n8n-url "$task_n8n_url"
echo 'MADAR: http://localhost:8000. JSON: var/n8n-import/. Workflows installed inactive; no customer messages sent.'
