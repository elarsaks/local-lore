#!/bin/sh
set -eu

SCRIPT_DIR=$(CDPATH='' cd -- "$(dirname -- "$0")" && pwd)
# shellcheck source=scripts/lib.sh
. "$SCRIPT_DIR/lib.sh"
locallore_require_runtime
locallore_require_docker
locallore_compose exec -T locallore \
  /app/.venv/bin/python -m locallore doctor

container_ids=$(docker ps -q \
  --filter label=com.docker.compose.project=locallore \
  --filter label=com.docker.compose.service=locallore)
if [ "$(printf '%s\n' "$container_ids" | sed '/^$/d' | wc -l | tr -d ' ')" != "1" ]; then
  echo "Expected exactly one running LocalLore service container." >&2
  exit 1
fi
binding=$(docker port locallore 8000/tcp)
if [ "$binding" != "127.0.0.1:8765" ]; then
  echo "LocalLore port is not loopback-only: $binding" >&2
  exit 1
fi
curl -fsS --max-time 3 "http://127.0.0.1:8765/healthz" >/dev/null
bad_host=$(curl -sS --max-time 3 -o /dev/null -w '%{http_code}' \
  -X POST -H "Host: invalid.example" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" -d '{}' \
  "http://127.0.0.1:8765/mcp")
bad_origin=$(curl -sS --max-time 3 -o /dev/null -w '%{http_code}' \
  -X POST -H "Origin: https://invalid.example" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" -d '{}' \
  "http://127.0.0.1:8765/mcp")
if [ "$bad_host" != "421" ] ||
   [ "$bad_origin" != "403" ]; then
  echo "LocalLore HTTP security checks failed " \
    "(host=$bad_host origin=$bad_origin)." >&2
  exit 1
fi
echo "ok: exactly one loopback-only LocalLore daemon with Host/Origin protection"
