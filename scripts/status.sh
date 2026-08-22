#!/bin/sh
set -eu

SCRIPT_DIR=$(CDPATH='' cd -- "$(dirname -- "$0")" && pwd)
# shellcheck source=scripts/lib.sh
. "$SCRIPT_DIR/lib.sh"
locallore_require_runtime
locallore_require_docker

PORT=$(locallore_port)
locallore_compose ps locallore
curl -fsS --max-time 3 "http://127.0.0.1:$PORT/statusz"
printf '\n'
