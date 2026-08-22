# Configuration reference

The container supplies these environment-backed settings. Defaults are defined
by `Settings.from_env()`.

| Variable | Default | Purpose |
| --- | --- | --- |
| `LOCALLORE_DB` | `/data/locallore.db` | SQLite database path |
| `LOCALLORE_SESSIONS` | `/sessions` | Root directory scanned recursively for JSONL files |
| `LOCALLORE_MODEL_PATH` | `/models` | Local embedding-model cache |
| `LOCALLORE_EMBEDDING_MODEL` | `BAAI/bge-small-en-v1.5` | FastEmbed model name |
| `LOCALLORE_EMBEDDING_DIMENSION` | `384` | Expected stored vector dimension |
| `LOCALLORE_EMBEDDING_BATCH_SIZE` | `64` | Messages embedded per batch |

Runtime polling and debounce defaults are class settings rather than
environment variables:

| Setting | Default | Purpose |
| --- | --- | --- |
| `watcher_interval` | `2.0` seconds | Delay between metadata scans |
| `watcher_debounce` | `0.5` seconds | Quiet period before a refresh |

The manual installer also recognizes `CLAUDE_PROJECTS_DIR` to choose the host
session directory. This value configures the Compose bind mount; it is distinct
from the in-container `LOCALLORE_SESSIONS` path.

## Fixed network interface

LocalLore publishes the service at `http://127.0.0.1:8765/mcp`. The host port
and expected Host/Origin values are intentionally fixed by the runtime security
model.
