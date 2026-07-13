#!/bin/sh
set -eu

PLUGIN_ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
SESSIONS_DIR=${CLAUDE_PROJECTS_DIR:-${HOME}/.claude/projects}

if ! command -v docker >/dev/null 2>&1; then
  echo "LocalLore requires Docker, but docker was not found on PATH." >&2
  exit 1
fi

if [ ! -d "$SESSIONS_DIR" ]; then
  echo "LocalLore session directory does not exist: $SESSIONS_DIR" >&2
  echo "Set CLAUDE_PROJECTS_DIR to the directory containing Claude project sessions." >&2
  exit 1
fi

export CLAUDE_PROJECTS_DIR=$SESSIONS_DIR
exec docker compose --project-name locallore --project-directory "$PLUGIN_ROOT" -f "$PLUGIN_ROOT/compose.yaml" run --rm -T locallore mcp
