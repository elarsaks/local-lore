# LocalLore 0.2.0 Release Notes

LocalLore 0.2.0 replaces per-session stdio containers with one persistent,
authenticated Streamable HTTP daemon.

## Highlights

- Any number of Claude Code sessions share one fixed `locallore` Compose service.
- A health-first `headersHelper` reconnects or starts the installed image without
  rebuilding or downgrading it.
- JSONL changes are polled, debounced, and processed by one background worker.
- Create, append, completed-tail, truncate, replace, rename, and deletion changes
  are supported; deletion cascades through all derived index rows.
- Searches use the last committed WAL snapshot during refresh.
- One lazy embedding model and inference lock serve indexing and queries.
- Status includes daemon uptime, transport, refresh state/timestamps, queue/error
  state, watcher interval, and last-refresh add/remove counts.
- Installation, update, status, logs, refresh, restart, stop, doctor, and
  confirmed uninstall scripts all use the fixed Compose project.

## Security and networking

The HTTP endpoint is bound to `127.0.0.1`, protected by a random persistent
bearer token, and rejects unexpected Host and browser Origin values. Existing
read-only mounts, read-only root filesystem, unprivileged UID/GID, dropped
capabilities, PID limit, `no-new-privileges`, and bounded tmpfs remain.

Docker Desktop did not expose a published host port from an `internal: true`
network during the implementation spike. Version 0.2 therefore uses a standard
bridge network, which enables outbound connectivity at the container boundary.
LocalLore performs local-files-only model inference and contains no runtime
network client or telemetry, but this release does not claim Docker-enforced
egress isolation.

## Compatibility

The three MCP tool names and input schemas are unchanged. Databases migrate in
place and remain in the fixed `locallore_locallore-data` volume.
