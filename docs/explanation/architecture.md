# Architecture

LocalLore is one local daemon with four responsibilities: observe session
files, maintain an index, retrieve memories, and expose those capabilities to
Claude Code through MCP.

## System context (C4 level 1)

```mermaid
C4Context
    title LocalLore system context
    Person(user, "Developer", "Works in Claude Code")
    System(claude, "Claude Code", "MCP client and session producer")
    System(locallore, "LocalLore", "Private session-memory system")
    System_Ext(docker, "Docker", "Runs the persistent LocalLore container")

    Rel(user, claude, "Works with")
    Rel(claude, locallore, "Searches memories", "MCP over loopback HTTP")
    Rel(claude, locallore, "Writes session history read by")
    Rel(docker, locallore, "Hosts")
```

## Containers and components (C4 levels 2–3)

```mermaid
C4Container
    title LocalLore containers and major components
    Person_Ext(claude, "Claude Code")
    Container_Boundary(runtime, "LocalLore container") {
        Component(mcp, "MCP server", "FastMCP / Starlette", "Status, search, and context tools")
        Component(watcher, "Source watcher", "asyncio", "Detects JSONL metadata changes")
        Component(indexer, "Index worker", "Python", "Parses, checkpoints, and embeds messages")
        Component(retriever, "Hybrid retriever", "SQLite FTS5 + NumPy", "Fuses keyword and vector rankings")
        Component(model, "Embedding model", "FastEmbed", "Produces local 384-dimensional vectors")
    }
    ContainerDb(sqlite, "Local index", "SQLite WAL", "Messages, FTS rows, file operations, embeddings, checkpoints")
    ContainerDb(sessions, "Claude sessions", "JSONL files", "Read-only source history")

    Rel(claude, mcp, "Calls", "Streamable HTTP on 127.0.0.1:8765")
    Rel(watcher, sessions, "Scans metadata")
    Rel(indexer, sessions, "Reads changed bytes")
    Rel(indexer, model, "Embeds new or stale messages")
    Rel(indexer, sqlite, "Commits index updates")
    Rel(mcp, retriever, "Delegates searches")
    Rel(retriever, model, "Embeds query")
    Rel(retriever, sqlite, "Reads committed index")
```

## Runtime behavior

The watcher and a single indexing worker run as asynchronous background tasks.
CPU- and I/O-bound refresh work moves to a thread. One lazily initialized
embedding model is shared by indexing and queries, and an inference lock
serializes access to it.

SQLite uses WAL mode so interactive readers can continue reading the last
committed index while a refresh transaction is in progress. A failed refresh
records an error and retries without discarding the previously committed data.

## Design boundaries

- Session history is input, mounted read-only; LocalLore never edits it.
- SQLite is derived state and may be recreated.
- The MCP endpoint is loopback-only and intended for trusted local clients.
- Embedding inference and search remain local at runtime.
- Tool results expose structured retrieval, not arbitrary SQL access.
