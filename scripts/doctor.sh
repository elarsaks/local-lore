#!/bin/sh
set -eu

PLUGIN_ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
. "$PLUGIN_ROOT/scripts/lib.sh"
locallore_require_runtime
locallore_require_docker
locallore_compose exec -T locallore \
  /app/.venv/bin/python -m locallore doctor

PORT=$(locallore_env_value LOCALLORE_PORT "$LOCALLORE_RUNTIME_ENV")
TOKEN=$(locallore_env_value LOCALLORE_TOKEN "$LOCALLORE_RUNTIME_ENV")
container_ids=$(docker ps -q \
  --filter label=com.docker.compose.project=locallore \
  --filter label=com.docker.compose.service=locallore)
if [ "$(printf '%s\n' "$container_ids" | sed '/^$/d' | wc -l | tr -d ' ')" != "1" ]; then
  echo "Expected exactly one running LocalLore service container." >&2
  exit 1
fi
binding=$(docker port locallore 8000/tcp)
if [ "$binding" != "127.0.0.1:$PORT" ]; then
  echo "LocalLore port is not loopback-only: $binding" >&2
  exit 1
fi
curl -fsS --max-time 3 "http://127.0.0.1:$PORT/healthz" >/dev/null
unauthorized=$(curl -sS --max-time 3 -o /dev/null -w '%{http_code}' \
  -X POST "http://127.0.0.1:$PORT/mcp")
bad_host=$(curl -sS --max-time 3 -o /dev/null -w '%{http_code}' \
  -X POST -H "Authorization: Bearer $TOKEN" -H "Host: invalid.example" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" -d '{}' \
  "http://127.0.0.1:$PORT/mcp")
bad_origin=$(curl -sS --max-time 3 -o /dev/null -w '%{http_code}' \
  -X POST -H "Authorization: Bearer $TOKEN" \
  -H "Origin: https://invalid.example" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" -d '{}' \
  "http://127.0.0.1:$PORT/mcp")
if [ "$unauthorized" != "401" ] ||
   [ "$bad_host" != "421" ] ||
   [ "$bad_origin" != "403" ]; then
  echo "LocalLore HTTP security checks failed " \
    "(unauthorized=$unauthorized host=$bad_host origin=$bad_origin)." >&2
  exit 1
fi
echo "ok: exactly one loopback-only, authenticated LocalLore daemon"
