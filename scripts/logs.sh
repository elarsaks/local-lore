#!/bin/sh
set -eu

PLUGIN_ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
. "$PLUGIN_ROOT/scripts/lib.sh"
locallore_require_runtime
locallore_require_docker
exec docker compose -p locallore \
  --project-directory "$LOCALLORE_ACTIVE_ROOT" \
  --env-file "$LOCALLORE_RUNTIME_ENV" \
  -f "$LOCALLORE_ACTIVE_ROOT/compose.yaml" logs "$@" locallore
