---
description: Configure how much Claude Code history LocalLore indexes
---

Configure LocalLore in a user-friendly conversation. This command is also the
manual fallback for the onboarding offer Claude makes after installation.

If `locallore_status` is available, call it first. If LocalLore is already
configured, show the current absolute cutoff and explain that changing it
rebuilds the derived local index but never edits Claude session files. If the
MCP server is not connected yet, continue with first-run setup; the bootstrap
script builds the runtime before configuration.

Ask the user to choose exactly one history window:

- today (`today`, from 00:00 UTC today)
- one week (`1_week`)
- one month (`1_month`, recommended)
- three months (`3_months`)
- one year (`1_year`)
- all available history (`all`)

Before applying the choice, explain that LocalLore reads Claude session history
read-only and stores a plaintext derived index in a private Docker volume. Warn
that the initial Docker build downloads dependencies and the embedding model,
and that indexing can use significant CPU for several minutes, especially for
all history. Explain that runtime processing remains offline and later refreshes
are incremental.

Only after explicit confirmation, use the Bash tool to run the following command
with the selected value in place of `HISTORY`:

```sh
"${CLAUDE_PLUGIN_ROOT}/scripts/setup.sh" HISTORY "${CLAUDE_PLUGIN_DATA}"
```

Allow the command to finish; do not ask the user to open a separate terminal.
Report the returned cutoff and completion state. If LocalLore was not connected
before setup, tell the user to run `/reload-plugins` once. Do not claim setup
succeeded if the script exits nonzero.
