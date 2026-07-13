#!/bin/sh
set -eu

PLUGIN_DATA_DIR=${1:-}
if [ -n "$PLUGIN_DATA_DIR" ] && [ -f "$PLUGIN_DATA_DIR/setup-complete" ]; then
  exit 0
fi

cat <<'EOF'
LocalLore has been installed but has not completed first-run setup. If setup has not already been offered or declined in this conversation, proactively offer to set it up now. Explain that it reads the user's local Claude Code session history read-only, stores a plaintext derived index in a private Docker volume, and performs all runtime processing offline. Docker with Compose v2 is required. The first setup downloads/builds the runtime and embedding model, and indexing can use significant CPU for several minutes. Do not start setup without the user's confirmation. If they agree, ask them to choose today, one week, one month (recommended), three months, one year, or all available history, then follow the locallore setup skill. Clarify that build output concerns runtime/model installation; the later indexing phase reports the actual imported and embedded message counts. Do not require the user to know or type /locallore:setup. If the user previously declined in this conversation, do not repeat the offer; answer their current request normally.
EOF
