#!/bin/sh
set -eu

SCRIPT_DIR=$(CDPATH='' cd -- "$(dirname -- "$0")" && pwd)
# shellcheck source=scripts/lib.sh
. "$SCRIPT_DIR/lib.sh"
locallore_require_runtime
locallore_require_docker

if [ "${1:-}" != "--yes" ]; then
  printf 'Delete the LocalLore container and SQLite index volume? [y/N] ' >&2
  read -r answer
  case "$answer" in
    y|Y|yes|YES) ;;
    *) echo "Uninstall cancelled." >&2; exit 1 ;;
  esac
fi

locallore_compose down --volumes --remove-orphans
rm -f "$LOCALLORE_RUNTIME_ENV"
rmdir "$LOCALLORE_DATA_DIR" 2>/dev/null || true
echo "LocalLore container and derived SQLite index volume were deleted."
echo "LocalLore runtime configuration and bearer token were deleted."
echo "Claude session history was not modified."
