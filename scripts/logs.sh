#!/bin/sh
set -eu

. "$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)/lib.sh"
locallore_require_runtime
locallore_require_docker
locallore_compose_logs "$@"
