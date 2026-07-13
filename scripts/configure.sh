#!/bin/sh
set -eu

if [ "$#" -ne 1 ]; then
  echo "Usage: $0 today|1_week|1_month|3_months|1_year|all" >&2
  exit 2
fi

PLUGIN_ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
SESSIONS_DIR=${CLAUDE_PROJECTS_DIR:-${HOME}/.claude/projects}
export CLAUDE_PROJECTS_DIR=$SESSIONS_DIR
exec docker compose --project-name locallore --project-directory "$PLUGIN_ROOT" -f "$PLUGIN_ROOT/compose.yaml" run --rm -T locallore configure "$1"
