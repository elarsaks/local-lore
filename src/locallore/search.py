from __future__ import annotations

import re
import sqlite3
from typing import TypedDict

MAX_RESULTS = 25
MAX_CONTEXT = 10
EXCERPT_LENGTH = 500


class SearchResult(TypedDict):
    session_id: str
    message_id: str
    project: str | None
    timestamp: str | None
    role: str
    score: float
    excerpt: str
    files: list[str]


class SearchResponse(TypedDict):
    results: list[SearchResult]
    index: dict[str, object]


def _fts_query(query: str) -> str:
    terms = re.findall(r"\w+", query, flags=re.UNICODE)
    if not terms:
        raise ValueError("query must contain at least one searchable term")
    return " OR ".join(f'"{term}"' for term in terms[:32])


def search_messages(
    connection: sqlite3.Connection,
    query: str,
    *,
    project: str | None = None,
    after: str | None = None,
    before: str | None = None,
    role: str | None = None,
    files: list[str] | None = None,
    limit: int = 8,
) -> SearchResponse:
    if role is not None and role not in {"user", "assistant", "tool"}:
        raise ValueError("role must be user, assistant, or tool")
    limit = max(1, min(limit, MAX_RESULTS))
    clauses = ["messages_fts MATCH ?"]
    parameters: list[object] = [_fts_query(query)]
    for sql, value in (
        ("s.project = ?", project),
        ("m.timestamp >= ?", after),
        ("m.timestamp < ?", before),
        ("m.role = ?", role),
    ):
        if value is not None:
            clauses.append(sql)
            parameters.append(value)
    for path in files or []:
        clauses.append(
            "EXISTS (SELECT 1 FROM file_operations f "
            "WHERE f.message_id = m.id AND f.path = ?)"
        )
        parameters.append(path)
    parameters.append(limit * 4)
    rows = connection.execute(
        "SELECT m.id, m.session_id, s.project, m.timestamp, m.role, m.text, "
        "bm25(messages_fts) AS rank "
        "FROM messages_fts JOIN messages m ON m.rowid = messages_fts.rowid "
        "JOIN sessions s ON s.id = m.session_id WHERE "
        + " AND ".join(clauses)
        + " ORDER BY rank, m.timestamp DESC LIMIT ?",
        parameters,
    ).fetchall()
    results: list[SearchResult] = []
    seen_text: set[str] = set()
    for row in rows:
        normalized_text = " ".join(row["text"].split()).casefold()
        if normalized_text in seen_text:
            continue
        seen_text.add(normalized_text)
        paths = [
            item[0]
            for item in connection.execute(
                "SELECT path FROM file_operations WHERE message_id = ? ORDER BY path",
                (row["id"],),
            )
        ]
        results.append(
            {
                "session_id": row["session_id"],
                "message_id": row["id"],
                "project": row["project"],
                "timestamp": row["timestamp"],
                "role": row["role"],
                "score": round(1.0 / (1.0 + abs(row["rank"])), 6),
                "excerpt": row["text"][:EXCERPT_LENGTH],
                "files": paths,
            }
        )
        if len(results) == limit:
            break
    refresh = connection.execute(
        "SELECT max(updated_at), count(*) FILTER (WHERE last_error IS NOT NULL) FROM import_files"
    ).fetchone()
    return {
        "results": results,
        "index": {"last_refresh": refresh[0], "refresh_errors": refresh[1]},
    }


def get_context(
    connection: sqlite3.Connection,
    session_id: str,
    message_id: str,
    *,
    before: int = 3,
    after: int = 3,
) -> dict[str, object]:
    before = max(0, min(before, MAX_CONTEXT))
    after = max(0, min(after, MAX_CONTEXT))
    target = connection.execute(
        "SELECT source_line FROM messages WHERE id = ? AND session_id = ?",
        (message_id, session_id),
    ).fetchone()
    if target is None:
        raise ValueError("message was not found in the requested session")
    rows = connection.execute(
        "SELECT id, role, timestamp, text, source_line FROM messages "
        "WHERE session_id = ? AND source_line BETWEEN ? AND ? ORDER BY source_line",
        (session_id, target[0] - before, target[0] + after),
    ).fetchall()
    return {
        "session_id": session_id,
        "selected_message_id": message_id,
        "messages": [
            {
                "message_id": row["id"],
                "role": row["role"],
                "timestamp": row["timestamp"],
                "text": row["text"][:EXCERPT_LENGTH],
            }
            for row in rows
        ],
    }
