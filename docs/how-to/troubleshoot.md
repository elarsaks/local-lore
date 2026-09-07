# Troubleshoot LocalLore

## Run the diagnostic suite

Start with:

```bash
./scripts/doctor.sh
```

It checks the runtime configuration, database migrations, FTS5 support, local
model inference, service container count, loopback binding, and HTTP
Host/Origin defenses.

## Inspect state and logs

```bash
./scripts/status.sh
./scripts/logs.sh
```

In `status.sh`, inspect `refresh_state`, `last_background_error`, and the most
recent refresh counters. A transient indexing error does not make committed
search data unavailable; the worker retries with exponential backoff capped at
30 seconds.

## The daemon is stopped

Rerun setup:

```text
/locallore:setup
```

For a checkout-based installation, run `./scripts/install.sh` instead.

## The session directory is missing

Marketplace installs expect `~/.claude/projects`. For a checkout, provide the
actual directory during installation:

```bash
CLAUDE_PROJECTS_DIR=/path/to/projects ./scripts/install.sh
```

The directory is mounted read-only into the container.

## Search misses a recent message

The watcher polls source metadata every two seconds and debounces bursts for
half a second. Wait briefly, then inspect `locallore_status`. Files that end in
an incomplete JSONL line are safely checkpointed before that line; the record
is imported after a newline completes it.

## Port 8765 is unavailable

LocalLore uses fixed host port `8765` on `127.0.0.1`. Stop the conflicting
process or container, then rerun setup. Do not publish the service on a public
interface; its security model trusts local processes running as your user.
