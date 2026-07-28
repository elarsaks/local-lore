"""Incrementally import session files into SQLite."""

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
    files_added: int = 0
    files_removed: int = 0
    messages_added: int = 0
    messages_removed: int = 0
    errors: int = 0


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _import_file(
    connection: sqlite3.Connection,
    source: SourceFile,
    checkpoint: sqlite3.Row | None,
) -> tuple[int, int, int]:
    if (
        checkpoint
        and checkpoint["identity"] == source.identity
        and checkpoint["size_bytes"] == source.size_bytes
        and checkpoint["mtime_ns"] == source.mtime_ns
    ):
        return 0, 0, 0
    rebuild = bool(
        checkpoint
        and (
            checkpoint["identity"] != source.identity
            or source.size_bytes < checkpoint["offset_bytes"]
        )
    )
    offset = 0 if rebuild or checkpoint is None else checkpoint["offset_bytes"]
    line_number = 0 if rebuild or checkpoint is None else checkpoint["last_line"]
    added = errors = removed = 0
    if rebuild:
        removed = connection.execute(
            "SELECT count(*) FROM messages m "
            "JOIN sessions s ON s.id = m.session_id "
            "WHERE s.source_path = ?",
            (source.relative_path,),
        ).fetchone()[0]
        connection.execute(
            "DELETE FROM sessions WHERE source_path = ?", (source.relative_path,)
        )
    session_metadata: dict[str, tuple[str | None, str | None]] = {}
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
            previous_metadata = session_metadata.get(parsed.session_id)
            current_metadata = (parsed.project, parsed.cwd)
            if previous_metadata is None or any(
                value is not None and value != previous
                for value, previous in zip(
                    current_metadata, previous_metadata, strict=True
                )
            ):
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
                session_metadata[parsed.session_id] = tuple(
                    value if value is not None else previous
                    for value, previous in zip(
                        current_metadata,
                        previous_metadata or (None, None),
                        strict=True,
                    )
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
            stored_message_id = parsed.message_id
            if cursor.rowcount == 0:
                stored = connection.execute(
                    "SELECT id FROM messages WHERE id = ? OR "
                    "(session_id = ? AND source_line = ? AND content_hash = ?)",
                    (
                        parsed.message_id,
                        parsed.session_id,
                        line_number,
                        content_hash,
                    ),
                ).fetchone()
                if stored is None:
                    raise sqlite3.IntegrityError(
                        "ignored message could not be resolved"
                    )
                stored_message_id = stored["id"]
            for path, operation in parsed.file_operations:
                connection.execute(
                    "INSERT OR IGNORE INTO file_operations(message_id, path, operation) VALUES (?, ?, ?)",
                    (stored_message_id, path, operation),
                )
        final_offset = handle.tell()
    error_text = f"{errors} malformed record(s)" if errors else None
    connection.execute(
        "INSERT INTO import_files(path, identity, size_bytes, mtime_ns, offset_bytes, last_line, last_error, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?) "
        "ON CONFLICT(path) DO UPDATE SET identity=excluded.identity, size_bytes=excluded.size_bytes, mtime_ns=excluded.mtime_ns, offset_bytes=excluded.offset_bytes, last_line=excluded.last_line, last_error=excluded.last_error, updated_at=excluded.updated_at",
        (
            source.relative_path,
            source.identity,
            source.size_bytes,
            source.mtime_ns,
            final_offset,
            line_number,
            error_text,
            _now(),
        )
    )
    return added, errors, removed


def import_sessions(connection: sqlite3.Connection, root: Path) -> ImportResult:
    sources = discover(root)
    checkpoints = {
        row["path"]: row
        for row in connection.execute("SELECT * FROM import_files").fetchall()
    }
    changed = added = errors = files_added = 0
    files_removed = messages_removed = 0
    source_paths = {source.relative_path for source in sources}
    with connection:
        missing_paths = sorted(set(checkpoints) - source_paths)
        for path in missing_paths:
            removed = connection.execute(
                "SELECT count(*) FROM messages m "
                "JOIN sessions s ON s.id = m.session_id "
                "WHERE s.source_path = ?",
                (path,),
            ).fetchone()[0]
            connection.execute(
                "DELETE FROM sessions WHERE source_path = ?", (path,)
            )
            connection.execute("DELETE FROM import_files WHERE path = ?", (path,))
            files_removed += 1
            messages_removed += removed
        for source in sources:
            checkpoint = checkpoints.get(source.relative_path)
            is_changed = not checkpoint or (
                checkpoint["identity"],
                checkpoint["size_bytes"],
                checkpoint["mtime_ns"],
            ) != (source.identity, source.size_bytes, source.mtime_ns)
            if checkpoint is None:
                files_added += 1
            file_added, file_errors, file_removed_messages = _import_file(
                connection, source, checkpoint
            )
            changed += int(is_changed)
            added += file_added
            errors += file_errors
            messages_removed += file_removed_messages
    return ImportResult(
        files_seen=len(sources),
        files_changed=changed,
        files_added=files_added,
        files_removed=files_removed,
        messages_added=added,
        messages_removed=messages_removed,
        errors=errors,
    )
