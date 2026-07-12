CREATE TABLE IF NOT EXISTS import_files (
    path TEXT PRIMARY KEY,
    identity TEXT,
    size_bytes INTEGER NOT NULL,
    mtime_ns INTEGER NOT NULL,
    offset_bytes INTEGER NOT NULL DEFAULT 0,
    last_line INTEGER NOT NULL DEFAULT 0,
    last_error TEXT,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS sessions (
    id TEXT PRIMARY KEY,
    source_path TEXT NOT NULL,
    project TEXT,
    cwd TEXT,
    title TEXT,
    started_at TEXT,
    ended_at TEXT,
    imported_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS messages (
    id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    source_line INTEGER NOT NULL,
    role TEXT NOT NULL,
    raw_type TEXT NOT NULL,
    timestamp TEXT,
    text TEXT NOT NULL,
    content_hash TEXT NOT NULL,
    UNIQUE(session_id, source_line, content_hash)
);

CREATE INDEX IF NOT EXISTS messages_session_id ON messages(session_id);
