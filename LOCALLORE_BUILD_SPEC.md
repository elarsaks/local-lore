# LocalLore Build Specification

This document is an implementation brief for building **LocalLore**, a clean Python rewrite inspired by the session-memory functionality in [Flex](https://github.com/damiandelmas/flex). It is intended to be copied into a new repository and given to Codex as the primary build specification.

LocalLore is a Claude Code plugin that indexes local Claude Code session history and lets the user ask questions about past work with:

```text
/remember <question>
```

Example:

```text
/remember why did we remove the HTTP MCP server from Flex?
```

LocalLore must run locally in Docker with runtime networking disabled. It must not send session content, queries, embeddings, or metadata over the network.

## 1. Product definition

LocalLore is an offline memory layer for Claude Code. It reads Claude Code's local JSONL session files, stores normalized session data in SQLite, builds keyword and semantic indexes, and exposes a small MCP server over stdio.

The product has one primary workflow:

```text
Claude Code session files
        ↓
incremental indexing at MCP startup
        ↓
SQLite + FTS5 + local embeddings
        ↓
LocalLore MCP search tool
        ↓
/remember asks Claude to search and synthesize an answer
```

Version one is intentionally narrow. It supports Claude Code session history only. It is not a general document indexer, generic SQL framework, plugin platform, repository indexer, or web service.

## 2. Non-negotiable requirements

- The implementation language is Python 3.12 or newer.
- The product is distributed as a Claude Code plugin.
- The user-facing activation command is `/remember`.
- The MCP server communicates over stdin/stdout only.
- Runtime executes in Docker with `network_mode: none`.
- Runtime must work without DNS, HTTP, package downloads, model downloads, or external APIs.
- Claude session files are mounted read-only.
- SQLite data is stored in a named Docker volume.
- Sessions are incrementally indexed every time the MCP server starts.
- Repeated indexing of unchanged input is idempotent.
- Search supports SQLite FTS5 and local semantic embeddings.
- The implementation should be small, typed, testable, and easy to understand.
- Do not copy Flex's broad generic module, cell, plugin, daemon, SOMA, or arbitrary-SQL architectures.

## 3. Reference implementation

Use the current Flex repository only to understand source data and useful retrieval behavior:

- Repository: [github.com/damiandelmas/flex](https://github.com/damiandelmas/flex)
- Claude session importer: [`flex/modules/claude_code/compile/worker.py`](https://github.com/damiandelmas/flex/blob/main/flex/modules/claude_code/compile/worker.py)
- Claude session views: [`flex/modules/claude_code/stock/views`](https://github.com/damiandelmas/flex/tree/main/flex/modules/claude_code/stock/views)
- Claude session presets: [`flex/modules/claude_code/stock/presets`](https://github.com/damiandelmas/flex/tree/main/flex/modules/claude_code/stock/presets)
- MCP behavior: [`flex/mcp_server.py`](https://github.com/damiandelmas/flex/blob/main/flex/mcp_server.py)
- Current Docker pattern: [`docker-compose.yml`](https://github.com/damiandelmas/flex/blob/main/docker-compose.yml)
- Current offline model setup: [`Dockerfile`](https://github.com/damiandelmas/flex/blob/main/Dockerfile)

These links may move as Flex evolves. When working from a local checkout, prefer inspecting the corresponding files in that checkout.

Reimplement only behavior LocalLore needs. Do not translate files line by line. Preserve useful ideas such as incremental JSONL ingestion, session/message normalization, FTS, local embeddings, and file-operation extraction while designing simpler boundaries.

## 4. Scope

### Version-one features

- Discover Claude Code JSONL session files below a configured session directory.
- Incrementally import new or changed session records.
- Store sessions, messages, tool calls, and observed file operations.
- Associate sessions with a project and working directory when the source data contains them.
- Index human-readable message content with SQLite FTS5.
- Generate embeddings locally from a model included in the image.
- Perform hybrid keyword and semantic search.
- Return compact evidence with session, project, timestamp, role, and relevant file paths.
- Expose MCP tools for search and status.
- Provide `/remember` instructions that make Claude retrieve evidence before answering.
- Persist the database between ephemeral MCP container runs.

### Explicitly out of scope

- HTTP transport or exposed ports.
- Runtime network access.
- A persistent host daemon.
- General filesystem or Markdown indexing.
- Arbitrary user-defined cells or modules.
- External plugin discovery.
- Arbitrary SQL supplied by Claude.
- URL identity, content-addressed storage, or the full SOMA subsystem.
- Cross-machine synchronization.
- Cloud storage, telemetry, analytics, or remote inference.
- Editing or deleting Claude's source session files.
- A broad end-user CLI.

## 5. Recommended repository layout

```text
locallore/
├── .claude-plugin/
│   └── plugin.json
├── commands/
│   └── remember.md
├── skills/
│   └── remember/
│       └── SKILL.md
├── .mcp.json
├── scripts/
│   ├── mcp.sh
│   ├── build.sh
│   ├── index.sh
│   └── doctor.sh
├── src/
│   └── locallore/
│       ├── __init__.py
│       ├── __main__.py
│       ├── config.py
│       ├── db.py
│       ├── schema.sql
│       ├── discovery.py
│       ├── parser.py
│       ├── importer.py
│       ├── embeddings.py
│       ├── search.py
│       ├── models.py
│       ├── mcp_server.py
│       └── status.py
├── tests/
│   ├── fixtures/
│   │   └── sessions/
│   ├── test_parser.py
│   ├── test_importer.py
│   ├── test_search.py
│   └── test_mcp.py
├── Dockerfile
├── compose.yaml
├── pyproject.toml
├── uv.lock
├── LICENSE
└── README.md
```

Keep modules cohesive. Do not add repository/service/manager classes unless they remove real duplication. Prefer small functions and a few explicit dataclasses over a framework.

## 6. Claude Code plugin surface

### Plugin manifest

Create `.claude-plugin/plugin.json` using the current Claude Code plugin manifest schema. Keep its metadata minimal and valid. Conceptually it should identify:

```json
{
  "name": "locallore",
  "description": "Offline local memory for Claude Code sessions",
  "version": "0.1.0"
}
```

Before implementation, verify the current Claude Code plugin manifest fields rather than assuming this illustrative shape is complete.

### MCP configuration

Create `.mcp.json` so Claude launches the plugin-provided script rather than Python directly:

```json
{
  "mcpServers": {
    "locallore": {
      "command": "${CLAUDE_PLUGIN_ROOT}/scripts/mcp.sh"
    }
  }
}
```

The exact variable expansion supported by the current Claude Code plugin system must be verified during implementation. The launcher must resolve paths reliably when invoked outside the plugin directory.

### `/remember` command

`commands/remember.md` should accept the rest of the command as the user's question. It should instruct Claude to:

1. Search LocalLore before answering.
2. Begin with the user's wording rather than inventing a broad query.
3. Use project, date, and file filters when the prompt provides those clues.
4. Fetch more context only if initial evidence is insufficient.
5. Synthesize an answer rather than dumping search rows.
6. Cite session timestamps, projects, and files when useful.
7. Separate evidence from inference.
8. Say clearly when no reliable memory was found.

Illustrative content:

```markdown
Search LocalLore for evidence that answers this question:

$ARGUMENTS

Use the LocalLore MCP search tool before answering. Prefer evidence from the
current project unless the question names another project. Summarize the past
work clearly, mention relevant dates and files, and label uncertain inferences.
Do not expose raw database rows unless the user asks for them.
```

### Remember skill

`skills/remember/SKILL.md` should activate for questions about past Claude Code work even when the user does not explicitly type `/remember`. Keep `/remember` as the predictable explicit entrypoint.

The skill should cover prompts such as:

- "How did we fix this before?"
- "Why was this design changed?"
- "Find the session where we discussed the migration."
- "What did I work on last week in this repository?"
- "Which files were involved in the authentication fix?"

The skill must not claim that search results are ground truth. Claude sessions record discussions and actions, which may later have been reverted or superseded.

## 7. Runtime and Docker design

### Runtime lifecycle

Each MCP launch should use an ephemeral container attached to a persistent data volume:

```text
Claude starts scripts/mcp.sh
        ↓
docker compose run --rm -T locallore mcp
        ↓
apply database migrations
        ↓
incrementally scan and index sessions
        ↓
start MCP stdio loop
        ↓
serve searches until Claude closes stdin
        ↓
container exits; named volume remains
```

Indexing at startup is acceptable for version one. Start the MCP protocol only after indexing completes so behavior is deterministic and simple. Optimize later only if measured startup time becomes unacceptable.

### Compose configuration

Use a service similar to:

```yaml
services:
  locallore:
    build: .
    network_mode: none
    stdin_open: true
    read_only: true
    cap_drop:
      - ALL
    security_opt:
      - no-new-privileges:true
    environment:
      LOCALLORE_DB: /data/locallore.db
      LOCALLORE_SESSIONS: /sessions
      HOME: /tmp/home
    volumes:
      - "${CLAUDE_PROJECTS_DIR:-${HOME}/.claude/projects}:/sessions:ro"
      - "locallore-data:/data"
    tmpfs:
      - /tmp:size=256m
    command: ["mcp"]

volumes:
  locallore-data:
```

Test the nested environment-variable default with Docker Compose on supported platforms. If Compose interpolation is unreliable, require `CLAUDE_PROJECTS_DIR` in `scripts/mcp.sh` and pass a fully resolved absolute path to Compose.

Do not mount the Docker socket, entire home directory, Git credentials, SSH directory, repository roots, or Claude configuration. The only host data needed at runtime is Claude's projects/session directory, mounted read-only.

### Launcher script

`scripts/mcp.sh` must:

- Use `set -eu`.
- Resolve the plugin root from the script's own location.
- Resolve `${CLAUDE_PROJECTS_DIR:-$HOME/.claude/projects}` on the host.
- Fail with a helpful stderr message if Docker or the session directory is unavailable.
- Execute `docker compose run --rm -T locallore mcp`.
- Preserve stdin and stdout for MCP.
- Send diagnostics and Docker progress to stderr, never stdout.
- Never enable networking.

Because stdout carries JSON-RPC, no launcher or server log line may be printed there.

### Image construction

The Docker build may use the network to install locked dependencies and acquire the embedding model. Runtime may not.

The final image must contain:

- Application source.
- Locked Python dependencies.
- SQLite with FTS5 support.
- Tokenizer assets.
- The complete local embedding model.
- Schema and migrations.

Use a multi-stage Dockerfile if it materially reduces the final image. Do not add complexity solely to minimize a modest image-size difference.

The final image should run as a non-root user when compatible with the named volume. Ensure that user can write `/data` and `/tmp`, but not application files.

## 8. Python application design

### Configuration

Use one frozen dataclass populated from environment variables:

```python
@dataclass(frozen=True, slots=True)
class Settings:
    database_path: Path
    sessions_path: Path
    model_path: Path
    embedding_dimension: int
```

Validate configuration once at startup. Avoid reading environment variables throughout the application.

### Domain models

Use small typed dataclasses for normalized data:

```python
@dataclass(frozen=True, slots=True)
class Session:
    id: str
    source_path: str
    project: str | None
    cwd: str | None
    started_at: datetime | None

@dataclass(frozen=True, slots=True)
class Message:
    id: str
    session_id: str
    role: str
    timestamp: datetime | None
    text: str
    raw_type: str

@dataclass(frozen=True, slots=True)
class FileOperation:
    message_id: str
    path: str
    operation: str
```

Keep raw Claude payloads available only where needed for debugging. Do not make arbitrary JSON blobs the primary query model.

### Database ownership

Use Python's `sqlite3` unless a demonstrated requirement needs another driver. Configure:

```sql
PRAGMA journal_mode = WAL;
PRAGMA foreign_keys = ON;
PRAGMA busy_timeout = 30000;
```

Use explicit transactions. One startup process performs writes, followed by read-heavy MCP queries, so a complex asynchronous database layer is unnecessary.

Do not introduce an ORM. SQL is central to the project and should remain visible.

## 9. SQLite schema

Start with a compact schema resembling the following. Adjust names where testing reveals a better source mapping.

```sql
CREATE TABLE schema_migrations (
    version INTEGER PRIMARY KEY,
    applied_at TEXT NOT NULL
);

CREATE TABLE import_files (
    path TEXT PRIMARY KEY,
    identity TEXT,
    size_bytes INTEGER NOT NULL,
    mtime_ns INTEGER NOT NULL,
    offset_bytes INTEGER NOT NULL DEFAULT 0,
    last_line INTEGER NOT NULL DEFAULT 0,
    last_error TEXT,
    updated_at TEXT NOT NULL
);

CREATE TABLE sessions (
    id TEXT PRIMARY KEY,
    source_path TEXT NOT NULL,
    project TEXT,
    cwd TEXT,
    title TEXT,
    started_at TEXT,
    ended_at TEXT,
    imported_at TEXT NOT NULL
);

CREATE TABLE messages (
    id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    source_line INTEGER,
    role TEXT NOT NULL,
    raw_type TEXT NOT NULL,
    timestamp TEXT,
    text TEXT NOT NULL,
    content_hash TEXT NOT NULL,
    UNIQUE(session_id, source_line, content_hash)
);

CREATE TABLE tool_calls (
    id TEXT PRIMARY KEY,
    message_id TEXT NOT NULL REFERENCES messages(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    input_json TEXT,
    output_text TEXT
);

CREATE TABLE file_operations (
    id INTEGER PRIMARY KEY,
    message_id TEXT NOT NULL REFERENCES messages(id) ON DELETE CASCADE,
    path TEXT NOT NULL,
    operation TEXT NOT NULL,
    UNIQUE(message_id, path, operation)
);

CREATE TABLE embeddings (
    message_id TEXT PRIMARY KEY REFERENCES messages(id) ON DELETE CASCADE,
    model_id TEXT NOT NULL,
    dimension INTEGER NOT NULL,
    vector BLOB NOT NULL
);

CREATE VIRTUAL TABLE messages_fts USING fts5(
    text,
    content='messages',
    content_rowid='rowid',
    tokenize='unicode61'
);
```

Add FTS synchronization triggers or explicitly update FTS in the importer. Whichever approach is chosen, cover it with tests.

Store embeddings as contiguous little-endian float32 bytes. Record the model identifier and dimension. Do not silently mix vectors from different models.

## 10. Session discovery and incremental ingestion

Claude Code generally stores project sessions below `~/.claude/projects`. Treat the format as external and evolving.

### Discovery

- Recursively find `*.jsonl` files under the mounted session directory.
- Sort paths for deterministic processing.
- Ignore symlinks that resolve outside the mounted root.
- Record per-file size and nanosecond modification time.
- Continue indexing other files when one file is malformed.

### Checkpointing

For each JSONL file, store:

- Path.
- A best-effort file identity when available.
- Last observed size and modification time.
- Last committed byte offset.
- Last committed line number.
- Last error.

If the file is unchanged, skip it. If it grew, seek to the last committed byte offset and parse appended complete lines. If it shrank or its identity changed, rebuild only data originating from that file inside a transaction.

Never advance the checkpoint beyond uncommitted records. A crash may cause replay, but uniqueness constraints must make replay safe.

### Parsing

Build tolerant parsing around dictionaries rather than rigidly deserializing the entire external event schema. Validate the fields LocalLore depends on and preserve unknown event types without crashing.

Handle at minimum:

- User messages.
- Assistant messages.
- Tool-use requests.
- Tool results.
- Session identifiers.
- Timestamps.
- Working directory and project metadata when available.
- File paths mentioned in common read, write, edit, and shell tool calls.

Keep extraction functions pure where possible so they can be tested against small JSON fixtures.

### Idempotency

The following must hold:

```text
index(input); snapshot database
index(unchanged input); snapshot database
assert snapshots are logically equivalent
```

Do not use current timestamps in a way that makes unchanged indexing mutate rows.

## 11. Embeddings

Use a small local sentence-embedding model that can run offline through ONNX Runtime or another dependable local Python runtime. Prefer reusing the model family already proven by Flex if licensing and distribution permit it.

Requirements:

- Model and tokenizer are downloaded during image build, never runtime.
- Record model name, version/revision, dimension, and content checksum.
- Batch new messages for inference.
- Normalize vectors once before storing them.
- Skip empty or trivial content.
- Embed user and assistant text; do not embed large raw tool outputs by default.
- Re-embed only when content or configured model changes.

Wrap inference behind a narrow interface:

```python
class Embedder(Protocol):
    @property
    def model_id(self) -> str: ...

    @property
    def dimension(self) -> int: ...

    def encode(self, texts: Sequence[str]) -> numpy.ndarray: ...
```

Do not allow the embedding dependency to leak into parsing, database migrations, or MCP protocol code.

## 12. Search design

Expose domain-oriented search rather than arbitrary SQL.

### MCP search input

```json
{
  "query": "why did we remove the HTTP MCP server?",
  "project": "flex",
  "after": "2026-01-01",
  "before": null,
  "files": [],
  "limit": 8
}
```

All fields except `query` are optional. Cap `limit` at a small safe maximum such as 25.

### Hybrid retrieval

Implement a simple, explainable pipeline:

1. Retrieve up to a bounded number of FTS5 candidates using BM25.
2. Retrieve semantic candidates using cosine similarity over normalized vectors.
3. Apply project, date, role, and file filters.
4. Fuse rankings with reciprocal rank fusion or a similarly simple method.
5. Avoid returning many adjacent messages with identical content.
6. Return compact excerpts plus stable identifiers.

For version one, loading normalized vectors into an in-memory NumPy matrix at MCP startup is acceptable. Measure memory usage and search latency before adopting a SQLite vector extension or separate vector database.

### Search output

Return structured evidence:

```json
{
  "results": [
    {
      "session_id": "...",
      "message_id": "...",
      "project": "flex",
      "timestamp": "2026-07-11T12:00:00Z",
      "role": "assistant",
      "score": 0.82,
      "excerpt": "...",
      "files": ["docker-compose.yml"]
    }
  ],
  "index": {
    "last_refresh": "...",
    "refresh_errors": 0
  }
}
```

Do not return unrestricted raw message bodies by default. Excerpts should be long enough to support synthesis but bounded to protect context.

Optionally add a second tool to retrieve surrounding messages for a known session/message ID. This is preferable to making the initial search response excessively large.

## 13. MCP server

Expose only these tools initially:

### `locallore_search`

Searches indexed Claude Code history. Input uses the structured search schema above.

### `locallore_context`

Returns a bounded number of messages surrounding a selected message within the same session. Inputs:

```json
{
  "session_id": "...",
  "message_id": "...",
  "before": 3,
  "after": 3
}
```

### `locallore_status`

Returns:

- Schema version.
- Last refresh time.
- Number of sessions and messages.
- Number of embedded messages.
- Embedding model ID.
- Files with import errors.

Use the official Python MCP SDK unless there is a compelling compatibility issue. Keep transport code thin. All business behavior should live in importer and search modules that tests can call without MCP.

Strictly reserve stdout for MCP protocol messages. Configure logging to stderr.

## 14. Application entrypoints

The container needs only a minimal internal command dispatcher:

```bash
python -m locallore mcp
python -m locallore index
python -m locallore doctor
```

These are operational entrypoints for Docker and tests, not a broad end-user CLI.

- `mcp`: migrate, index, then serve MCP over stdio.
- `index`: migrate and perform one incremental indexing pass.
- `doctor`: verify paths, database writability, FTS5, model assets, inference, and network-disabled assumptions where observable.

Use `argparse`; do not add a CLI framework for three commands.

## 15. Error handling and observability

- Use Python logging directed to stderr.
- Include file path and line number for malformed JSONL records.
- Record per-file errors in SQLite so `locallore_status` can report them.
- Continue after a malformed line when the next line is independently parseable.
- Roll back a file's current import transaction on database or embedding failure.
- Never corrupt or advance checkpoints after a failed transaction.
- Avoid logging full private message content.
- Exit nonzero when startup cannot open the database, load the model, or initialize MCP.

Use exceptions for unexpected failures and explicit result/count objects for ordinary indexing outcomes.

## 16. Security and privacy

LocalLore handles private development conversations. Treat privacy as a core feature.

- Runtime network is disabled by Docker, not merely by application convention.
- No telemetry or crash reporting.
- No remote model/API fallback.
- Source sessions are mounted read-only.
- Database volume is the only persistent writable storage.
- Container runs without Linux capabilities and with `no-new-privileges`.
- No host repository mount is required.
- Tool inputs are bounded and validated.
- MCP output is size-limited.
- SQL parameters are always bound, never interpolated from user input.
- Do not expose arbitrary SQL execution.

Document that anyone with access to the Docker volume can read the indexed session content. Encryption at rest is not required for version one, but the limitation must be stated.

## 17. Testing requirements

Use `pytest`. Tests must not depend on the developer's real Claude history.

### Unit tests

- Parse representative user, assistant, tool-use, and tool-result events.
- Ignore or preserve unknown event types safely.
- Extract file operations from representative tool inputs.
- Normalize timestamps and project metadata.
- Encode and decode float32 embedding blobs.
- Fuse keyword and semantic rankings deterministically.

### Database tests

- Create and migrate a fresh temporary database.
- Apply migrations twice safely.
- Import a fixture file.
- Reimport it unchanged without logical changes.
- Append lines and import only the appended records.
- Handle truncation by rebuilding only the affected source file.
- Keep FTS synchronized with messages.
- Enforce foreign keys and uniqueness constraints.

### Search tests

- Keyword search finds exact terms.
- Semantic search uses a deterministic fake embedder in most tests.
- Project/date/file filters work.
- Hybrid ranking is stable.
- Results are bounded and deduplicated.
- Context retrieval cannot cross session boundaries.

### MCP tests

- Initialize the server over in-memory streams or subprocess stdio.
- List the three expected tools.
- Validate tool inputs.
- Perform a search against a fixture database.
- Confirm logs do not contaminate stdout.

### Docker tests

- Build the image from the lockfile.
- Run indexing with `--network none`.
- Run an embedding smoke test with `--network none`.
- Confirm the session mount is read-only.
- Confirm data persists in the named volume across ephemeral containers.
- Confirm MCP startup succeeds with Docker networking disabled.

## 18. Development milestones

Build vertical slices in this order.

### Milestone 1: plugin skeleton and offline container

- Create the plugin manifest, `/remember` command, skill, `.mcp.json`, scripts, Dockerfile, and Compose file.
- Implement a minimal MCP server with `locallore_status`.
- Verify Claude can launch it through Docker with `network_mode: none`.

Acceptance criterion: Claude sees the LocalLore MCP server and can call status while the container has no network.

### Milestone 2: schema and JSONL ingestion

- Add migrations, discovery, tolerant parsing, and checkpoints.
- Import sessions and messages from anonymized fixtures.
- Prove idempotency and append-only refresh.

Acceptance criterion: repeated startup against unchanged fixtures produces no logical database changes.

### Milestone 3: keyword memory

- Add FTS5 and structured filters.
- Implement `locallore_search` and `locallore_context`.
- Wire `/remember` to retrieve and synthesize evidence.

Acceptance criterion: `/remember` answers fixture questions using FTS evidence with useful session metadata.

### Milestone 4: semantic memory

- Add the local embedding model to the image.
- Add batched embedding and in-memory cosine search.
- Fuse FTS and semantic results.

Acceptance criterion: semantic queries work with `network_mode: none` and retrieve relevant paraphrases absent from keyword matches.

### Milestone 5: hardening and documentation

- Add Docker security settings, doctor checks, error reporting, performance measurements, and complete tests.
- Document installation, upgrades, data deletion, privacy, and troubleshooting.

Acceptance criterion: a clean machine with Docker and Claude Code can install the plugin, build once online, and then use `/remember` offline.

## 19. Definition of done

LocalLore version 0.1 is complete when:

- The repository installs as a Claude Code plugin using the current supported plugin mechanism.
- `/remember <question>` reliably triggers LocalLore-backed retrieval.
- MCP runs through an ephemeral Docker container using stdio.
- Docker runtime has networking disabled.
- The embedding model is available without runtime downloads.
- Session sources are mounted read-only.
- SQLite data persists in a named volume.
- Every MCP startup performs an idempotent incremental indexing pass.
- FTS and semantic retrieval both work.
- Search output includes enough evidence for Claude to synthesize trustworthy answers.
- Malformed session records do not destroy the index.
- Unit, database, search, MCP, and offline Docker tests pass.
- The README explains installation, use, privacy, troubleshooting, and complete data removal.
- No unnecessary generic framework from Flex has been reproduced.

## 20. Guidance for Codex implementing this specification

When this file is handed to Codex in the new LocalLore repository:

1. Inspect the repository before editing and follow any local `AGENTS.md` instructions.
2. Verify current Claude Code plugin and MCP configuration formats from authoritative documentation before finalizing manifests.
3. Create a short implementation plan aligned with the milestones above.
4. Implement one vertical milestone at a time and test it before continuing.
5. Prefer the simplest implementation satisfying current acceptance criteria.
6. Do not introduce abstractions for hypothetical future clients, data sources, transports, or vector stores.
7. Use anonymized, minimal session fixtures; never commit real Claude session history.
8. Keep stdout protocol-clean and send all diagnostics to stderr.
9. Test the actual Docker path with networking disabled, not only local Python execution.
10. Record deliberate deviations from this specification in the README or an architecture decision document.

The desired outcome is not a renamed copy of Flex. It is a small, comprehensible, offline Claude Code memory plugin whose complete architecture can be understood by reading a handful of Python modules.
