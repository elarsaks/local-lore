#!/bin/sh
set -eu

PLUGIN_ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
. "$PLUGIN_ROOT/scripts/lib.sh"
locallore_require_runtime
locallore_require_docker

PORT=$(locallore_env_value LOCALLORE_PORT "$LOCALLORE_RUNTIME_ENV")
TOKEN=$(locallore_env_value LOCALLORE_TOKEN "$LOCALLORE_RUNTIME_ENV")
locallore_compose ps locallore
curl -fsS --max-time 3 -H "Authorization: Bearer $TOKEN" \
  "http://127.0.0.1:$PORT/statusz"
printf '\n'
