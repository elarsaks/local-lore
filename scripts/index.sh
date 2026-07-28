#!/bin/sh
set -eu

. "$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)/lib.sh"
locallore_require_runtime
locallore_require_docker

PORT=$(locallore_port)
TOKEN=$(locallore_token)
curl -fsS --max-time 3 -X POST \
  -H "Authorization: Bearer $TOKEN" \
  "http://127.0.0.1:$PORT/admin/refresh"
printf '\n'
