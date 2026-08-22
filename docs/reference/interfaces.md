# Commands and tools reference

## Repository scripts

| Command | Purpose |
| --- | --- |
| `./scripts/install.sh` | Build, configure, start, and validate LocalLore |
| `./scripts/status.sh` | Show container and index status |
| `./scripts/logs.sh` | Follow daemon logs |
| `./scripts/doctor.sh` | Run health and security diagnostics |
| `./scripts/uninstall.sh` | Remove runtime state after confirmation |
| `./scripts/check.sh` | Run repository formatting, lint, type, and test gates |

## MCP tools

### `locallore_status`

Takes no arguments. Returns daemon version and uptime, index counts, refresh
state and timestamps, recent change counters, queued work, and the latest
background error.

### `locallore_search`

| Parameter | Type | Default | Constraint |
| --- | --- | --- | --- |
| `query` | `str` | required | Must not be blank |
| `project` | `str \| None` | `None` | Exact match |
| `after` | `str \| None` | `None` | Inclusive timestamp bound |
| `before` | `str \| None` | `None` | Exclusive timestamp bound |
| `role` | `str \| None` | `None` | `user`, `assistant`, or `tool` |
| `files` | `list[str] \| None` | `None` | Exact associated paths |
| `limit` | `int` | `8` | Clamped to 1–25 |

Returns ranked excerpts and index freshness metadata.

### `locallore_context`

| Parameter | Type | Default | Constraint |
| --- | --- | --- | --- |
| `session_id` | `str` | required | Must identify the result's session |
| `message_id` | `str` | required | Must identify a message in that session |
| `before` | `int` | `3` | Clamped to 0–10 |
| `after` | `int` | `3` | Clamped to 0–10 |

Returns messages ordered by their source line, with each text field limited to
500 characters.

## HTTP health routes

| Route | Purpose |
| --- | --- |
| `GET /healthz` | Non-sensitive process liveness |
| `GET /statusz` | Structured daemon and index status |
