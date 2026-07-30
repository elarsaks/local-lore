#!/bin/sh

# Read by every lifecycle script that sources this library.
# shellcheck disable=SC2034
LOCALLORE_PLUGIN_ROOT=$(CDPATH='' cd -- "$(dirname -- "$0")/.." && pwd)

locallore_data_dir() {
  if [ -n "${CLAUDE_PLUGIN_DATA:-}" ]; then
    printf '%s\n' "$CLAUDE_PLUGIN_DATA"
  elif [ -n "${XDG_DATA_HOME:-}" ]; then
    printf '%s\n' "$XDG_DATA_HOME/locallore"
  else
    printf '%s\n' "${HOME}/.local/share/locallore"
  fi
}

locallore_canonical_data_dir() {
  if [ -n "${XDG_DATA_HOME:-}" ]; then
    printf '%s\n' "$XDG_DATA_HOME/locallore"
  else
    printf '%s\n' "${HOME}/.local/share/locallore"
  fi
}

locallore_env_value() {
  key=$1
  file=$2
  sed -n "s/^${key}=//p" "$file" | sed -n '1p'
}

locallore_port() {
  locallore_env_value LOCALLORE_PORT "$LOCALLORE_RUNTIME_ENV"
}

locallore_token() {
  locallore_env_value LOCALLORE_TOKEN "$LOCALLORE_RUNTIME_ENV"
}

locallore_require_runtime() {
  LOCALLORE_DATA_DIR=$(locallore_data_dir)
  LOCALLORE_RUNTIME_ENV=$LOCALLORE_DATA_DIR/runtime.env
  if [ ! -f "$LOCALLORE_RUNTIME_ENV" ] &&
     [ -f "$(locallore_canonical_data_dir)/runtime.env" ]; then
    LOCALLORE_DATA_DIR=$(locallore_canonical_data_dir)
    LOCALLORE_RUNTIME_ENV=$LOCALLORE_DATA_DIR/runtime.env
  fi
  if [ ! -f "$LOCALLORE_RUNTIME_ENV" ]; then
    echo "LocalLore is not installed. Run ./scripts/install.sh first." >&2
    exit 1
  fi
  LOCALLORE_ACTIVE_ROOT=$(locallore_env_value LOCALLORE_PLUGIN_ROOT "$LOCALLORE_RUNTIME_ENV")
  if [ ! -f "$LOCALLORE_ACTIVE_ROOT/compose.yaml" ]; then
    echo "LocalLore active runtime is unavailable: $LOCALLORE_ACTIVE_ROOT" >&2
    echo "Run ./scripts/install.sh from the current plugin version." >&2
    exit 1
  fi
}

locallore_compose() {
  docker compose -p locallore \
    --project-directory "$LOCALLORE_ACTIVE_ROOT" \
    --env-file "$LOCALLORE_RUNTIME_ENV" \
    -f "$LOCALLORE_ACTIVE_ROOT/compose.yaml" "$@"
}

locallore_compose_logs() {
  locallore_compose logs "$@" locallore
}

locallore_require_docker() {
  if ! command -v docker >/dev/null 2>&1; then
    echo "LocalLore requires Docker, but docker was not found on PATH." >&2
    exit 1
  fi
  if ! docker compose version >/dev/null 2>&1; then
    echo "LocalLore requires Docker Compose v2 and a running Docker daemon." >&2
    exit 1
  fi
}

locallore_print_headers() {
  token=$1
  printf '{"Authorization":"Bearer %s"}\n' "$token"
}
