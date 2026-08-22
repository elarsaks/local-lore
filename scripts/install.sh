#!/bin/sh
set -eu

SCRIPT_DIR=$(CDPATH='' cd -- "$(dirname -- "$0")" && pwd)
# shellcheck source=scripts/lib.sh
. "$SCRIPT_DIR/lib.sh"

locallore_require_docker

DATA_DIR=$(locallore_data_dir)
RUNTIME_ENV=$DATA_DIR/runtime.env
SESSIONS_DIR=${CLAUDE_PROJECTS_DIR:-${HOME}/.claude/projects}
PORT=${LOCALLORE_PORT:-8765}
VERSION=0.3.0

case "$SESSIONS_DIR" in
  \~/*) SESSIONS_DIR=$HOME/${SESSIONS_DIR#\~/} ;;
esac

case "$PORT" in
  *[!0-9]*|'')
    echo "LocalLore port must be a number between 1024 and 65535." >&2
    exit 1
    ;;
esac
if [ "$PORT" -lt 1024 ] || [ "$PORT" -gt 65535 ]; then
  echo "LocalLore port must be between 1024 and 65535." >&2
  exit 1
fi
if [ ! -d "$SESSIONS_DIR" ]; then
  echo "LocalLore session directory does not exist: $SESSIONS_DIR" >&2
  echo "Set CLAUDE_PROJECTS_DIR to use a non-default session directory." >&2
  exit 1
fi

mkdir -p "$DATA_DIR"
chmod 700 "$DATA_DIR"

TEMP_ENV=$DATA_DIR/runtime.env.pending
umask 077
{
  printf 'LOCALLORE_PLUGIN_ROOT=%s\n' "$LOCALLORE_PLUGIN_ROOT"
  printf 'LOCALLORE_IMAGE=locallore:%s\n' "$VERSION"
  printf 'LOCALLORE_ACTIVE_VERSION=%s\n' "$VERSION"
  printf 'LOCALLORE_PORT=%s\n' "$PORT"
  printf 'CLAUDE_PROJECTS_DIR=%s\n' "$SESSIONS_DIR"
  printf 'LOCALLORE_WATCH_INTERVAL=2\n'
  printf 'LOCALLORE_IDLE_WATCH_INTERVAL=2\n'
  printf 'LOCALLORE_WATCH_DEBOUNCE=0.5\n'
} >"$TEMP_ENV"
chmod 600 "$TEMP_ENV"

# These variables are read by the Compose helpers sourced from lib.sh.
# shellcheck disable=SC2034
LOCALLORE_DATA_DIR=$DATA_DIR
# shellcheck disable=SC2034
LOCALLORE_RUNTIME_ENV=$TEMP_ENV
# shellcheck disable=SC2034
LOCALLORE_ACTIVE_ROOT=$LOCALLORE_PLUGIN_ROOT

conflicts=$(docker ps -aq \
  --filter label=com.docker.compose.service=locallore \
  --filter label=com.docker.compose.project!=locallore 2>/dev/null || true)
if [ -n "$conflicts" ]; then
  echo "A LocalLore container from another Compose project already exists." >&2
  echo "Stop or remove it before installing the fixed 'locallore' project." >&2
  exit 1
fi

echo "Building LocalLore $VERSION (the first build downloads the bundled model)..."
locallore_compose build locallore
echo "LocalLore image build complete."
mv "$TEMP_ENV" "$RUNTIME_ENV"
LOCALLORE_RUNTIME_ENV=$RUNTIME_ENV
echo "Starting the persistent LocalLore daemon..."
locallore_compose up -d --wait locallore
echo "LocalLore daemon started. Waiting for initial session indexing..."

deadline=150
elapsed=0
while [ "$deadline" -gt 0 ]; do
  status=$(curl -fsS --max-time 2 \
    "http://127.0.0.1:$PORT/statusz" 2>/dev/null || true)
  if printf '%s' "$status" | grep -q '"refresh_state":"idle"' &&
     printf '%s' "$status" | grep -q '"last_successful_refresh_at":"'; then
    break
  fi
  sleep 2
  deadline=$((deadline - 2))
  elapsed=$((elapsed + 2))
  if [ $((elapsed % 10)) -eq 0 ] && [ "$deadline" -gt 0 ]; then
    echo "Still indexing Claude sessions (${elapsed}s elapsed)..."
  fi
done
if [ "$deadline" -le 0 ]; then
  echo "LocalLore started, but initial indexing did not finish in time." >&2
  echo "Inspect ./scripts/logs.sh and retry ./scripts/install.sh." >&2
  exit 1
fi

echo "Initial session indexing complete."
echo "Running LocalLore health and security checks..."
"$LOCALLORE_PLUGIN_ROOT/scripts/doctor.sh"
echo "LocalLore is ready at http://127.0.0.1:$PORT/mcp"
