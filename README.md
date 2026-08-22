# LocalLore

LocalLore is a private memory layer for Claude Code. One persistent local
daemon incrementally indexes Claude Code session history and serves hybrid
SQLite FTS5 and local-embedding search to every Claude session over loopback-only
MCP Streamable HTTP.

This repository is a finished, pinned snapshot and is not actively maintained.
Review its locked dependencies and security assumptions before adopting it.

## Requirements

- Claude Code with plugin support
- Docker Desktop or Docker Engine with Docker Compose v2
- A Claude projects directory, normally `~/.claude/projects`

The initial image build needs internet access for pinned Python packages and the
embedding model. The model is bundled in the image and inference never falls
back to a remote service.

## Install

Add this repository as a Claude Code marketplace and install LocalLore:

```text
/plugin marketplace add elarsaks/local-lore
/plugin install locallore@locallore
/reload-plugins
/locallore:setup
```

The default user-scoped installation makes LocalLore available in every
project. During setup, LocalLore builds its container image, starts the
persistent daemon, waits for the initial index, and runs its health and security
checks. Rerun `/locallore:setup` after marketplace updates to activate the
updated daemon version.

## Install from a checkout or update manually

Run the same command for initial installation and every update:

```bash
./scripts/install.sh
```

Set a non-default session directory when needed:

```bash
CLAUDE_PROJECTS_DIR=/path/to/projects ./scripts/install.sh
```

Marketplace installs use port `8765` and `~/.claude/projects` automatically, so
plugin installation does not ask configuration questions. The manual installer
continues to accept `CLAUDE_PROJECTS_DIR` for checkout-based installs.

The installer validates Docker and the session path, creates mode-`0600` runtime
configuration, builds the image, starts the fixed `locallore` Compose project,
waits for initial background indexing, and runs production health/security
checks. Image builds and model downloads never occur during Claude startup.

Load the checkout with `claude --plugin-dir .`. The plugin connects directly to
`http://127.0.0.1:<port>/mcp`. Docker keeps the installed daemon running across
normal Claude sessions.

## Background indexing

The daemon polls JSONL source metadata, debounces bursts, and queues work through
one indexing worker. New, appended, completed-tail, truncated, replaced, renamed,
and deleted sources are handled incrementally. Source deletion cascades through
messages, file operations, full-text rows, and embeddings.

SQLite WAL readers continue using the last committed index during refresh. A
failed refresh records an error, keeps search available, and retries with bounded
backoff. One lazy embedding model and one inference lock are shared by background
embedding and interactive queries.

## Operations

```bash
./scripts/status.sh
./scripts/logs.sh
./scripts/doctor.sh
./scripts/uninstall.sh
```

Indexing runs automatically in the daemon. `uninstall.sh` asks for confirmation
before deleting the container, derived index volume, and runtime configuration;
Claude session files are never deleted.

Normal Claude sessions connect to the persistent HTTP daemon. If its container
is stopped manually, rerun `/locallore:setup` or `./scripts/install.sh` to start
it again.

## Privacy and security

- The MCP port is published only on `127.0.0.1`.
- Unexpected HTTP `Host` and browser `Origin` values are rejected to protect the
  loopback-only endpoint from browser and DNS-rebinding requests.
- Session history is bind-mounted read-only.
- The container filesystem is read-only, runs as UID/GID 65532, drops all Linux
  capabilities, forbids privilege escalation, limits PIDs, and uses bounded
  `noexec` tmpfs storage.
- The model is image-bundled and configured for local-files-only inference.
- There is no telemetry, crash reporting, remote inference fallback, or exposed
  arbitrary SQL.

The Compose network is a standard user-defined bridge because Docker Desktop
does not reliably publish host ports for `internal: true` networks. Consequently,
the container technically has outbound network access. LocalLore itself does
not make runtime network requests, but Docker-level egress isolation is not
claimed. Loopback binding and Host/Origin validation protect the local HTTP
endpoint. Local processes running as the current user are trusted and can access
LocalLore without authentication.

The SQLite volume contains plaintext conversation text and embeddings. LocalLore
does not provide encryption at rest; use host disk encryption and OS access
controls.

## Validation

```bash
./scripts/check.sh
claude plugin validate .
./scripts/doctor.sh
```

`doctor.sh` checks configuration, migrations, FTS5, model inference, one running
service container, loopback-only publication, and Host/Origin protection.
