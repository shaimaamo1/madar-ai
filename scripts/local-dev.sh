#!/usr/bin/env bash
# Run only on your computer. Uses your existing n8n; never creates its account.
set -euo pipefail
cd "$(dirname "$0")/.."
docker compose build app
# Initialization prompts for an API key securely and writes the ignored host .env.
docker compose run --rm --no-deps --interactive --tty \
  --user "$(id -u):$(id -g)" --volume "$PWD:/workspace" --workdir /workspace \
  --entrypoint python app -m scripts.local_n8n init --n8n-url http://localhost:5678
docker compose up -d app
# Attach an existing Docker n8n automatically when it is unambiguous.
task_candidates=()
while IFS="|" read -r task_image task_container; do
  if [[ "$task_image" == *n8n* && -n "$task_container" ]]; then task_candidates+=("$task_container"); fi
done < <(docker ps --filter publish=5678 --format '{{.Image}}|{{.Names}}')
if [[ ${#task_candidates[@]} -eq 1 ]]; then
  task_container="${task_candidates[0]}"
  task_networks=$(docker inspect --format '{{json .NetworkSettings.Networks}}' "$task_container")
  if [[ "$task_networks" != *'"madar-local"'* ]]; then
    docker network connect --alias n8n madar-local "$task_container"
  fi
elif [[ ${#task_candidates[@]} -gt 1 ]]; then
  echo 'Multiple containers publish port 5678. Select your n8n container with the documented network-connect command.'
  exit 1
else
  # A native n8n process calls MADAR through the host's loopback port.
  docker compose run --rm --no-deps --user "$(id -u):$(id -g)" \
    --volume "$PWD:/workspace" --workdir /workspace --entrypoint python app \
    -m scripts.local_n8n init --callback-url http://localhost:8000 --container-url http://host.docker.internal:5678
  docker compose up -d app
fi
# The helper uses the local .env; override only the request URL for container networking.
task_n8n_url=http://n8n:5678
if [[ ${#task_candidates[@]} -eq 0 ]]; then task_n8n_url=http://host.docker.internal:5678; fi
docker compose exec -T app python - <<'PY'
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
    raise SystemExit('MADAR did not become ready; inspect docker compose logs app locally.')
PY
docker compose run --rm --no-deps --volume "$PWD:/workspace" --workdir /workspace \
  --user "$(id -u):$(id -g)" --entrypoint python \
  -e MADAR_TEST_APP_URL=http://app:8000 app \
  -m scripts.local_n8n test --n8n-url "$task_n8n_url"
docker compose run --rm --no-deps --volume "$PWD:/workspace" --workdir /workspace \
  --user "$(id -u):$(id -g)" --entrypoint python app \
  -m scripts.local_n8n deploy --n8n-url "$task_n8n_url"
echo 'MADAR is ready at http://localhost:8000. Workflows are installed inactive. No customer messages sent.'
