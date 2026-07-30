#!/bin/sh
set -eu

SCRIPT_DIR=$(CDPATH='' cd -- "$(dirname -- "$0")" && pwd)
# shellcheck source=scripts/lib.sh
. "$SCRIPT_DIR/lib.sh"

locallore_require_runtime

PORT=$(locallore_port)
TOKEN=$(locallore_token)
IMAGE=$(locallore_env_value LOCALLORE_IMAGE "$LOCALLORE_RUNTIME_ENV")

if curl -fsS --max-time 1 "http://127.0.0.1:$PORT/healthz" >/dev/null 2>&1; then
  locallore_print_headers "$TOKEN"
  exit 0
fi

locallore_require_docker

if ! docker image inspect "$IMAGE" >/dev/null 2>&1; then
  echo "LocalLore image $IMAGE is missing; run ./scripts/install.sh." >&2
  exit 1
fi

if ! locallore_compose up -d --wait --wait-timeout 6 --no-build locallore >/dev/null 2>&1; then
  echo "LocalLore could not start within 10 seconds; run ./scripts/install.sh." >&2
  exit 1
fi

attempt=0
while [ "$attempt" -lt 3 ]; do
  if curl -fsS --max-time 1 "http://127.0.0.1:$PORT/healthz" >/dev/null 2>&1; then
    locallore_print_headers "$TOKEN"
    exit 0
  fi
  attempt=$((attempt + 1))
  sleep 1
done

echo "LocalLore did not become healthy; run ./scripts/install.sh." >&2
exit 1
