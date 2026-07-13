#!/bin/sh
set -eu

PLUGIN_ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
export CLAUDE_PROJECTS_DIR=${CLAUDE_PROJECTS_DIR:-/tmp}
exec docker compose --project-name locallore --project-directory "$PLUGIN_ROOT" -f "$PLUGIN_ROOT/compose.yaml" build locallore
