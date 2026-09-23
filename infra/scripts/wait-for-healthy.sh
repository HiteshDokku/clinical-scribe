#!/usr/bin/env bash
# Polls `docker compose ps` until every service reports healthy, or times out.
# Used by CI and by developers after `make dev` to know when it's safe to hit
# the gateway instead of guessing with a sleep.
set -euo pipefail

TIMEOUT_SECONDS="${1:-120}"
elapsed=0
interval=3

echo "Waiting up to ${TIMEOUT_SECONDS}s for all services to report healthy..."

while true; do
  unhealthy=$(docker compose ps --format json \
    | python3 -c "
import sys, json
count = 0
for line in sys.stdin:
    line = line.strip()
    if not line:
        continue
    svc = json.loads(line)
    health = svc.get('Health', '')
    if health and health != 'healthy':
        count += 1
print(count)
")

  if [ "$unhealthy" -eq 0 ]; then
    echo "All services healthy after ${elapsed}s."
    exit 0
  fi

  if [ "$elapsed" -ge "$TIMEOUT_SECONDS" ]; then
    echo "Timed out after ${TIMEOUT_SECONDS}s with ${unhealthy} service(s) still unhealthy."
    docker compose ps
    exit 1
  fi

  sleep "$interval"
  elapsed=$((elapsed + interval))
done
