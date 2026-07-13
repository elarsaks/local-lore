#!/bin/sh
set -eu

if [ "$#" -ne 2 ]; then
  echo "Usage: $0 today|1_week|1_month|3_months|1_year|all PLUGIN_DATA_DIR" >&2
  exit 2
fi

case "$1" in
  today|1_week|1_month|3_months|1_year|all) ;;
  *)
    echo "Unknown history window: $1" >&2
    exit 2
    ;;
esac

PLUGIN_ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
PLUGIN_DATA_DIR=$2
SESSIONS_DIR=${CLAUDE_PROJECTS_DIR:-${HOME}/.claude/projects}

progress() {
  STEP=$1
  LABEL=$2
  case "$STEP" in
    1) BAR="####----------------" ;;
    2) BAR="########------------" ;;
    3) BAR="############--------" ;;
    4) BAR="################----" ;;
    5) BAR="####################" ;;
  esac
  printf '\nLocalLore setup [%s] %s/5 — %s\n' "$BAR" "$STEP" "$LABEL" >&2
}

if ! command -v docker >/dev/null 2>&1; then
  echo "LocalLore requires Docker, but docker was not found on PATH." >&2
  exit 1
fi
if ! docker compose version >/dev/null 2>&1; then
  echo "LocalLore requires Docker Compose v2 and a running Docker installation." >&2
  exit 1
fi
if [ ! -d "$SESSIONS_DIR" ]; then
  echo "LocalLore session directory does not exist: $SESSIONS_DIR" >&2
  echo "Set CLAUDE_PROJECTS_DIR to the directory containing Claude project sessions." >&2
  exit 1
fi

export CLAUDE_PROJECTS_DIR=$SESSIONS_DIR
progress 1 "Building the offline runtime and downloading model assets"
"$PLUGIN_ROOT/scripts/build.sh"
progress 2 "Checking Docker, storage, SQLite, and model inference"
"$PLUGIN_ROOT/scripts/doctor.sh"
progress 3 "Saving the selected history window"
CUTOFF=$("$PLUGIN_ROOT/scripts/configure.sh" "$1")
progress 4 "Importing session history and generating embeddings"
"$PLUGIN_ROOT/scripts/index.sh"
mkdir -p "$PLUGIN_DATA_DIR"
printf '%s\n' "$CUTOFF" > "$PLUGIN_DATA_DIR/setup-complete"
progress 5 "Ready"

echo "LocalLore setup complete. History cutoff: $CUTOFF"
echo "Reload plugins with /reload-plugins if the LocalLore MCP server is not connected."
