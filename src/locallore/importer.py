from __future__ import annotations

import hashlib
import logging
import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from .discovery import SourceFile, discover
from .parser import decode_line, parse_record

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class ImportResult:
    files_seen: int = 0
    files_changed: int = 0
    messages_added: int = 0
    errors: int = 0


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _import_file(connection: sqlite3.Connection, source: SourceFile) -> tuple[int, int]:
    checkpoint = connection.execute(
        "SELECT * FROM import_files WHERE path = ?", (source.relative_path,)
    ).fetchone()
    if (
        checkpoint
        and checkpoint["identity"] == source.identity
        and checkpoint["size_bytes"] == source.size_bytes
        and checkpoint["mtime_ns"] == source.mtime_ns
    ):
        return 0, 0
    rebuild = bool(
        checkpoint
        and (
            checkpoint["identity"] != source.identity
            or source.size_bytes < checkpoint["offset_bytes"]
        )
    )
    offset = 0 if rebuild or checkpoint is None else checkpoint["offset_bytes"]
    line_number = 0 if rebuild or checkpoint is None else checkpoint["last_line"]
    added = errors = 0
    with connection:
        if rebuild:
            connection.execute("DELETE FROM sessions WHERE source_path = ?", (source.relative_path,))
        with source.path.open("rb") as handle:
            handle.seek(offset)
            while raw := handle.readline():
                if not raw.endswith(b"\n"):
                    handle.seek(-len(raw), 1)
                    break
                line_number += 1
                try:
                    parsed = parse_record(decode_line(raw), source.path, line_number)
                except (UnicodeDecodeError, ValueError) as exc:
                    errors += 1
                    logger.warning(
                        "Skipping malformed JSONL record %s:%d: %s",
                        source.relative_path,
                        line_number,
                        exc,
                    )
                    continue
                if parsed is None:
                    continue
                imported_at = parsed.timestamp or _now()
                connection.execute(
                    "INSERT INTO sessions(id, source_path, project, cwd, started_at, imported_at) VALUES (?, ?, ?, ?, ?, ?) "
                    "ON CONFLICT(id) DO UPDATE SET project=COALESCE(excluded.project, project), cwd=COALESCE(excluded.cwd, cwd)",
                    (
                        parsed.session_id,
                        source.relative_path,
                        parsed.project,
                        parsed.cwd,
                        parsed.timestamp,
                        imported_at,
                    ),
                )
                content_hash = hashlib.sha256(parsed.text.encode()).hexdigest()
                cursor = connection.execute(
                    "INSERT OR IGNORE INTO messages(id, session_id, source_line, role, raw_type, timestamp, text, content_hash) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        parsed.message_id,
                        parsed.session_id,
                        line_number,
                        parsed.role,
                        parsed.raw_type,
                        parsed.timestamp,
                        parsed.text,
                        content_hash,
                    ),
                )
                added += cursor.rowcount
                for path, operation in parsed.file_operations:
                    connection.execute(
                        "INSERT OR IGNORE INTO file_operations(message_id, path, operation) VALUES (?, ?, ?)",
                        (parsed.message_id, path, operation),
                    )
            final_offset = handle.tell()
        error_text = f"{errors} malformed record(s)" if errors else None
        connection.execute(
            "INSERT INTO import_files(path, identity, size_bytes, mtime_ns, offset_bytes, last_line, last_error, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?) "
            "ON CONFLICT(path) DO UPDATE SET identity=excluded.identity, size_bytes=excluded.size_bytes, mtime_ns=excluded.mtime_ns, offset_bytes=excluded.offset_bytes, last_line=excluded.last_line, last_error=excluded.last_error, updated_at=excluded.updated_at",
            (source.relative_path, source.identity, source.size_bytes, source.mtime_ns, final_offset, line_number, error_text, _now()),
        )
    return added, errors


def import_sessions(connection: sqlite3.Connection, root: Path) -> ImportResult:
    sources = discover(root)
    changed = added = errors = 0
    for source in sources:
        checkpoint = connection.execute(
            "SELECT identity, size_bytes, mtime_ns FROM import_files WHERE path = ?",
            (source.relative_path,),
        ).fetchone()
        is_changed = not checkpoint or tuple(checkpoint) != (
            source.identity,
            source.size_bytes,
            source.mtime_ns,
        )
        file_added, file_errors = _import_file(connection, source)
        changed += int(is_changed)
        added += file_added
        errors += file_errors
    return ImportResult(len(sources), changed, added, errors)
