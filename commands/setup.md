---
description: Install or update the LocalLore daemon
---

Run the LocalLore installer from the active plugin version:

```sh
CLAUDE_PLUGIN_DATA="${CLAUDE_PLUGIN_DATA}" \
CLAUDE_PLUGIN_OPTION_projects_directory="${user_config.projects_directory}" \
CLAUDE_PLUGIN_OPTION_port="${user_config.port}" \
"${CLAUDE_PLUGIN_ROOT}/scripts/install.sh"
```

Explain that the first installation builds the container image and downloads the
pinned embedding model, so it requires internet access and may take several
minutes. Preserve and report the installer's output. If installation succeeds,
tell the user that LocalLore is ready and suggest asking a question about past
Claude Code work. If it fails, summarize the error and recommend the most
relevant LocalLore diagnostic command.
