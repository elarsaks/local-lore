---
description: Install or update the LocalLore daemon
---

Before invoking the installer, tell the user that setup is starting. Explain
that the first installation builds the container image and downloads the pinned
embedding model, so it requires internet access and can take 30 minutes or
longer depending on the network, hardware, Docker build cache, and amount of
session history. Tell the user to keep Docker running and allow setup to finish.
Do not wait for the installer to finish before sending this first update.

Then run the LocalLore installer from the active plugin version:

```sh
CLAUDE_PLUGIN_DATA="${CLAUDE_PLUGIN_DATA}" \
"${CLAUDE_PLUGIN_ROOT}/scripts/install.sh"
```

Preserve and report the installer's phase and progress output. If installation
succeeds, tell the user that LocalLore is ready and suggest asking a question
about past Claude Code work. If it fails, summarize the error and recommend the
most relevant LocalLore diagnostic command.
