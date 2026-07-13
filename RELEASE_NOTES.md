# LocalLore 0.1.0 Release Notes

LocalLore 0.1.0 is the first release of an offline memory layer for Claude Code.

## User-visible behavior

- Incrementally indexes local Claude Code JSONL session history at MCP startup.
- Provides `/remember <question>` for retrieving and synthesizing evidence from
  earlier work.
- Combines SQLite FTS5 keyword retrieval with locally computed semantic
  embeddings.
- Exposes bounded `locallore_status`, `locallore_search`, and
  `locallore_context` MCP tools over stdio.
- Preserves the derived SQLite index in a Docker volume while using ephemeral
  runtime containers.

## Installation requirements

- Claude Code with plugin support.
- Docker Desktop or Docker Engine with Docker Compose v2.
- Python 3.12 or newer for development and running the tests outside Docker.
- A local Claude projects directory, normally `~/.claude/projects`.
- Internet access for the initial image build so pinned dependencies and the
  embedding model can be downloaded. Runtime use is offline.

See [README.md](README.md#install) for installation and validation commands.

## Privacy limitations

- LocalLore copies session text and derived embeddings into an unencrypted
  SQLite database in the `locallore-data` Docker volume.
- Anyone with access to that volume can read the indexed content. LocalLore
  relies on host disk encryption and operating-system access controls.
- Source sessions are mounted read-only, and runtime networking is disabled.
  There is no telemetry, remote inference fallback, or external API call.

## Known issues and limitations

- Version 0.1 indexes Claude Code session history only.
- Indexing completes before the MCP server starts, so startup time grows with
  the amount of new or changed history.
- The first image build requires network access; model assets are bundled into
  the resulting image for offline runtime use.
- Encryption at rest is not provided.
- Downgrading a database created by a newer release is not supported. Back up
  the Docker volume before attempting a downgrade.
- Search evidence reflects recorded discussions and actions; later work may
  have superseded or reverted them.
