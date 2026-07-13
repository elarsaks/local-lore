#!/bin/sh
set -eu

PLUGIN_ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
SESSIONS_DIR=${CLAUDE_PROJECTS_DIR:-${HOME}/.claude/projects}
export CLAUDE_PROJECTS_DIR=$SESSIONS_DIR
exec docker compose --project-name locallore --project-directory "$PLUGIN_ROOT" -f "$PLUGIN_ROOT/compose.yaml" run --rm -T locallore doctor
