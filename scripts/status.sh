#!/bin/sh
set -eu

. "$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)/lib.sh"
locallore_require_runtime
locallore_require_docker

PORT=$(locallore_port)
TOKEN=$(locallore_token)
locallore_compose ps locallore
curl -fsS --max-time 3 -H "Authorization: Bearer $TOKEN" \
  "http://127.0.0.1:$PORT/statusz"
printf '\n'
