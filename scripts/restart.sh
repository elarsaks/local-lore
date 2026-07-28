#!/bin/sh
set -eu

PLUGIN_ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
. "$PLUGIN_ROOT/scripts/lib.sh"
locallore_require_runtime
locallore_require_docker
locallore_compose restart locallore
locallore_compose up -d --wait --no-build locallore
