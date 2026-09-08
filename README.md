# LocalLore

LocalLore lets Claude Code search your earlier coding sessions. It runs locally
and does not send your conversations to a hosted search or embedding service.

## Requirements

- Claude Code with plugin support
- Docker with Docker Compose v2
- existing Claude Code sessions, normally in `~/.claude/projects`

## Install

Run these commands inside Claude Code:

```text
/plugin marketplace add elarsaks/local-lore
/plugin install locallore@locallore
/reload-plugins
/locallore:setup
```

The first setup builds the container image, downloads the pinned embedding
model, starts LocalLore, indexes your existing sessions, and checks that the
service is healthy. It can take 30 minutes or longer depending on your network,
hardware, Docker build cache, and amount of session history. Keep Docker
running and allow the setup command to finish. The first setup requires internet
access; search and embedding inference are local afterward.

## Search your sessions

Ask Claude to remember earlier work:

```text
/locallore:remember Why did we choose SQLite for this project?
```

You can also ask naturally:

```text
Search LocalLore for the session where we decided how to handle database migrations.
```

Add details when you know them, such as a project, date range, or file:

```text
Search LocalLore for discussions about ranking in the local-lore project
after 2026-01-01 involving src/locallore/search.py.
```

See [Search session history](https://elarsaks.github.io/local-lore/how-to/search-session-history/)
for all available filters and context controls.

## Check or repair the service

From a repository checkout:

```bash
./scripts/status.sh
./scripts/logs.sh
./scripts/doctor.sh
```

If the service has stopped or a marketplace update was installed, run
`/locallore:setup` again. For troubleshooting steps, see the
[troubleshooting guide](https://elarsaks.github.io/local-lore/how-to/troubleshoot/).

## Install from a checkout

Run the installer for both initial setup and updates:

```bash
./scripts/install.sh
```

To use a different Claude session directory:

```bash
CLAUDE_PROJECTS_DIR=/path/to/projects ./scripts/install.sh
```

Load the checkout as a development plugin with:

```bash
claude --plugin-dir .
```

## Uninstall

```bash
./scripts/uninstall.sh
```

The script asks before deleting the LocalLore container, derived SQLite index,
and runtime configuration. It never deletes Claude Code session files.

## Documentation

The [LocalLore documentation](https://elarsaks.github.io/local-lore/) contains
the complete usage guides, troubleshooting help, architecture, API reference,
and explanations of RAG, embeddings, keyword and vector search, indexing, and
MCP.

To preview it locally:

```bash
uv sync --locked --group docs
uv run --group docs mkdocs serve
```

Then open <http://127.0.0.1:8000/>.

## Project status

This repository is a finished, pinned snapshot and is not actively maintained.
Review its locked dependencies and security assumptions before adopting it.

LocalLore is licensed under the [MIT License](LICENSE).
