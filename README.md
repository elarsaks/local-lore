# LocalLore

LocalLore is an offline memory layer for Claude Code. It will index local Claude Code session history and make past work searchable through the `/remember` command.

## Milestone 1

This first slice provides the plugin skeleton and a minimal MCP server with `locallore_status`. Session indexing and search are planned for later milestones.

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

Run `/mcp` in Claude Code to confirm that the LocalLore server is connected. The available tool is `locallore_status`.

The container is configured with `network_mode: none`, mounts session files read-only, and stores future index data in the named `locallore-data` volume.

## Direct MCP smoke test

```bash
printf '%s\n' \
'{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-06-18","capabilities":{},"clientInfo":{"name":"test","version":"1"}}}' \
'{"jsonrpc":"2.0","method":"notifications/initialized","params":{}}' \
'{"jsonrpc":"2.0","id":2,"method":"tools/list","params":{}}' \
'{"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"locallore_status","arguments":{}}}' \
| CLAUDE_PROJECTS_DIR="$HOME/.claude/projects" docker compose run --rm -T locallore mcp
```

The status response is expected to show zero sessions and messages until indexing is implemented.

## Evals

The first eval suite defines the product contract for `/remember` before search is
implemented. It covers query fidelity, project/date/file filters, contextual
follow-up, evidence synthesis, provenance, and honest no-result behavior.

Run the deterministic eval checks with the rest of the test suite:

```bash
uv run pytest
```

The cases live in `evals/remember.yaml`. Future retrieval milestones can execute
the same cases against indexed fixtures while keeping these expected behaviors
stable.

## Privacy

Runtime networking is disabled by Docker. Local session files are never edited or uploaded. The SQLite index will live in the Docker volume, so anyone with access to that volume can read indexed session content.

## Development milestones

See [LOCALLORE_BUILD_SPEC.md](LOCALLORE_BUILD_SPEC.md) for the planned ingestion, keyword search, semantic search, and hardening milestones.
