# LocalLore

LocalLore is an offline memory layer for Claude Code. It incrementally indexes
local Claude Code session history and retrieves past work through `/remember`.
SQLite FTS5 and an image-bundled sentence-embedding model provide hybrid search;
the runtime container has no network interface.

## Requirements

- Claude Code with plugin support
- Docker Desktop or Docker Engine with Docker Compose v2
- A local Claude projects directory (normally `~/.claude/projects`)

The first image build needs internet access to download pinned Python packages
and the embedding model. Runtime use, indexing, diagnostics, and search are
offline.

## Install

Clone this repository, validate it, build the image, and run the diagnostic:

```bash
claude plugin validate .
CLAUDE_PROJECTS_DIR="$HOME/.claude/projects" ./scripts/build.sh
CLAUDE_PROJECTS_DIR="$HOME/.claude/projects" ./scripts/doctor.sh
```

Then load the checkout for a Claude Code session:

```bash
claude --plugin-dir .
```

Run `/mcp` to confirm that `locallore` is connected, then ask
`/remember <question>`. The MCP server exposes only `locallore_status`,
`locallore_search`, and `locallore_context`.

## Operations

Indexing happens automatically before MCP startup. To refresh explicitly:

```bash
CLAUDE_PROJECTS_DIR="$HOME/.claude/projects" ./scripts/index.sh
```

The importer is incremental and safe to rerun. It rebuilds only a source file
that was replaced or truncated. Malformed complete JSONL records are skipped,
reported with their path and line number on stderr, and exposed by
`locallore_status`; incomplete trailing records wait for the next refresh.

`./scripts/doctor.sh` verifies that the session mount is readable, the database
volume is writable, migrations and FTS5 work, foreign keys are enabled, local
model assets can run inference, and Compose supplied the offline-runtime marker.
It exits nonzero with an actionable error when a check fails.

## Upgrade

Pull the desired release and rebuild while online:

```bash
git pull --ff-only
CLAUDE_PROJECTS_DIR="$HOME/.claude/projects" ./scripts/build.sh
CLAUDE_PROJECTS_DIR="$HOME/.claude/projects" ./scripts/doctor.sh
```

The named `locallore-data` volume is retained and database migrations run at
startup. Back up that volume before downgrading; older releases are not promised
to understand newer schemas.

## Privacy and security

- Docker disables runtime networking with `network_mode: none`.
- Session history is bind-mounted read-only; LocalLore never edits it.
- The container filesystem is read-only, all Linux capabilities are dropped,
  privilege escalation is disabled, processes are limited, and the container
  runs as unprivileged UID/GID 65532.
- Only the SQLite index persists in the `locallore-data` Docker volume.
- There is no telemetry, crash reporting, remote model fallback, or API call.
- Search inputs and outputs are bounded and arbitrary SQL is not exposed.

The index contains plaintext copies and embeddings of private conversation data.
Anyone who can access the Docker volume can read it. LocalLore 0.1 does not
provide encryption at rest; rely on host disk encryption and OS access controls.

## Delete all indexed data

Find the Compose project and remove its volume (this is irreversible):

```bash
docker compose -f compose.yaml down
docker volume ls --filter name=locallore-data
docker volume rm local-lore_locallore-data
```

Compose derives the prefix from the checkout directory, so use the exact volume
name printed by `docker volume ls`. This removes only LocalLore's derived index,
not Claude session files. The next launch creates and rebuilds an empty index.

## Troubleshooting

- **Docker command not found or daemon unavailable:** install/start Docker, then
  confirm `docker compose version` succeeds.
- **Session directory does not exist:** set `CLAUDE_PROJECTS_DIR` to the directory
  containing Claude project session JSONL files.
- **MCP disconnects during startup:** run `./scripts/doctor.sh`; diagnostics stay
  on stderr so stdout remains valid MCP JSON-RPC.
- **Embedding assets missing:** rebuild the image while online. Runtime downloads
  are deliberately disabled.
- **Old or missing results:** run `./scripts/index.sh`, then inspect
  `locallore_status` for file-level import errors.
- **Permission denied for the volume:** ensure Docker can create/write its named
  volume; LocalLore intentionally runs as UID 65532.
- **Build works but offline runtime does not:** use the supplied Compose launchers.
  Directly running the image bypasses the enforced network and mount settings.

## Validation and performance

Run all deterministic unit, database, ingestion, keyword, semantic, MCP,
security, doctor, and evaluation-contract tests:

```bash
uv run pytest
```

The performance regression test measures hybrid search over 2,000 local vectors
and guards both peak Python allocation and elapsed search time with deliberately
generous CI thresholds. This provides a repeatable signal before considering a
SQLite vector extension. The production model smoke test is performed by
`doctor` inside the offline container.

For a direct MCP protocol smoke test, see [the build specification](LOCALLORE_BUILD_SPEC.md#13-mcp-server).

## Design

See [LOCALLORE_BUILD_SPEC.md](LOCALLORE_BUILD_SPEC.md) for the architecture,
security model, test requirements, and milestones.
