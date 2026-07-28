#!/bin/sh
set -eu

PLUGIN_ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
. "$PLUGIN_ROOT/scripts/lib.sh"
locallore_require_runtime
locallore_require_docker
locallore_compose stop locallore
echo "LocalLore stopped; the SQLite volume was preserved."
