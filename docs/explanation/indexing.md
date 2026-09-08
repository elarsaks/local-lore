---
description: Learn how LocalLore incrementally indexes appended, replaced, renamed, and deleted Claude Code session files.
---

# Incremental indexing

Indexing converts append-oriented JSONL session files into structured,
searchable records. Re-reading every file on every change would waste work, so
LocalLore checkpoints each source by path, filesystem identity, size, modified
time, byte offset, and last complete line.

```mermaid
flowchart TD
    A[Poll JSONL metadata] --> B{Snapshot changed?}
    B -- No --> A
    B -- Yes --> C[Debounce burst]
    C --> D[Queue one refresh]
    D --> E[Acquire index lock]
    E --> F[Discover current sources]
    F --> G{Source state}
    G -- New or appended --> H[Read from checkpoint]
    G -- Truncated or replaced --> I[Rebuild that source]
    G -- Deleted or renamed --> J[Remove old source records]
    H --> K[Parse complete JSONL lines]
    I --> K
    J --> L[Embed pending messages]
    K --> L
    L --> M[Commit SQLite transaction]
    M --> A
```

## Change handling

- **Unchanged file:** skip it using identity, size, and modification time.
- **Append:** seek to the stored byte offset and parse only new complete lines.
- **Incomplete tail:** leave the byte offset before the partial line so a later
  refresh can import it safely.
- **Truncation or replacement:** delete records associated with that source and
  rebuild it from byte zero.
- **Deletion or rename:** remove the missing source; foreign-key cascades clean
  up its messages, file operations, FTS rows, and embeddings. A renamed file is
  then discovered as new.
- **Malformed line:** record the error and continue with other lines.

Only one worker refreshes the index. File bursts coalesce through a debounce,
and refresh requests arriving during indexing queue another pass. Failures
retry with bounded exponential backoff.
