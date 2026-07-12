# LocalLore

LocalLore is an offline memory layer for Claude Code. It will index local Claude Code session history and make past work searchable through the `/remember` command.

## Milestone 4

LocalLore incrementally indexes normalized session and message data in SQLite.
SQLite FTS5 and a local ONNX sentence-embedding model provide hybrid retrieval
through `locallore_search`, while `locallore_context` retrieves a bounded window
around selected evidence. Search supports project, date, role, and file filters.
Keyword and semantic rankings are combined with reciprocal rank fusion.

## Requirements

- Claude Code
- Docker Desktop with Docker Compose
- A local Claude projects directory (normally `~/.claude/projects`)

## Try it locally

Validate the plugin and build the image:

```bash
claude plugin validate .
CLAUDE_PROJECTS_DIR="$HOME/.claude/projects" ./scripts/build.sh
```

Load the plugin for a Claude Code session:

```bash
claude --plugin-dir .
```

Run `/mcp` in Claude Code to confirm that the LocalLore server is connected. The
available tools are `locallore_status`, `locallore_search`, and
`locallore_context`. Use `/remember <question>` to search and synthesize evidence
from indexed sessions.

The container is configured with `network_mode: none`, mounts session files
read-only, and stores its SQLite index in the named `locallore-data` volume. The
embedding model is downloaded into the image during the build and is loaded with
runtime downloads disabled.

## Direct MCP smoke test

```bash
printf '%s\n' \
'{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-06-18","capabilities":{},"clientInfo":{"name":"test","version":"1"}}}' \
'{"jsonrpc":"2.0","method":"notifications/initialized","params":{}}' \
'{"jsonrpc":"2.0","id":2,"method":"tools/list","params":{}}' \
'{"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"locallore_status","arguments":{}}}' \
| CLAUDE_PROJECTS_DIR="$HOME/.claude/projects" docker compose run --rm -T locallore mcp
```

The status response reports the indexed session and message counts, last refresh,
and any import errors.

## Evals

The eval suite defines the product contract for `/remember`. It covers query
fidelity, project/date/file filters, contextual follow-up, evidence synthesis,
provenance, and honest no-result behavior.

Run the deterministic eval checks with the rest of the test suite:

```bash
uv run pytest
```

The cases live in `evals/remember.yaml` and `evals/retrieval.yaml`. The retrieval
evals are deterministic and make no model API calls; local ONNX inference does
not consume API tokens.

## Privacy

Runtime networking is disabled by Docker. Local session files are never edited or uploaded. The SQLite index will live in the Docker volume, so anyone with access to that volume can read indexed session content.

## Development milestones

See [LOCALLORE_BUILD_SPEC.md](LOCALLORE_BUILD_SPEC.md) for the planned ingestion, keyword search, semantic search, and hardening milestones.
