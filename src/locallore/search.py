from __future__ import annotations

import re
import sqlite3
from typing import TypedDict

import numpy as np

from .embeddings import Embedder, decode_vector

MAX_RESULTS = 25
MAX_CONTEXT = 10
EXCERPT_LENGTH = 500
RRF_K = 60


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


def _filters(
    *,
    project: str | None,
    after: str | None,
    before: str | None,
    role: str | None,
    files: list[str] | None,
) -> tuple[list[str], list[object]]:
    clauses: list[str] = []
    parameters: list[object] = []
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
    return clauses, parameters


def _keyword_ranking(
    connection: sqlite3.Connection,
    query: str,
    filters: list[str],
    parameters: list[object],
    candidate_limit: int,
) -> list[str]:
    try:
        fts_query = _fts_query(query)
    except ValueError:
        return []
    clauses = ["messages_fts MATCH ?", *filters]
    rows = connection.execute(
        "SELECT m.id FROM messages_fts "
        "JOIN messages m ON m.rowid = messages_fts.rowid "
        "JOIN sessions s ON s.id = m.session_id WHERE "
        + " AND ".join(clauses)
        + " ORDER BY bm25(messages_fts), m.timestamp DESC LIMIT ?",
        [fts_query, *parameters, candidate_limit],
    ).fetchall()
    return [row["id"] for row in rows]


def _semantic_ranking(
    connection: sqlite3.Connection,
    query: str,
    embedder: Embedder,
    filters: list[str],
    parameters: list[object],
    candidate_limit: int,
) -> list[str]:
    rows = connection.execute(
        "SELECT m.id, e.vector FROM embeddings e "
        "JOIN messages m ON m.id = e.message_id "
        "JOIN sessions s ON s.id = m.session_id "
        "WHERE e.model_id = ? AND e.dimension = ?"
        + (" AND " + " AND ".join(filters) if filters else ""),
        [embedder.model_id, embedder.dimension, *parameters],
    ).fetchall()
    if not rows:
        return []
    query_vector = np.asarray(embedder.encode_query(query), dtype=np.float32)
    norm = np.linalg.norm(query_vector)
    if norm == 0:
        raise ValueError("query embedding has zero length")
    query_vector /= norm
    matrix = np.vstack(
        [decode_vector(row["vector"], embedder.dimension) for row in rows]
    )
    scores = matrix @ query_vector
    best = np.argsort(-scores, kind="stable")[:candidate_limit]
    return [rows[index]["id"] for index in best]


def _fuse_rankings(*rankings: list[str]) -> list[tuple[str, float]]:
    scores: dict[str, float] = {}
    for ranking in rankings:
        for rank, message_id in enumerate(ranking, start=1):
            scores[message_id] = scores.get(message_id, 0.0) + 1.0 / (RRF_K + rank)
    return sorted(scores.items(), key=lambda item: (-item[1], item[0]))


def search_messages(
    connection: sqlite3.Connection,
    query: str,
    *,
    embedder: Embedder | None = None,
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
    if not query.strip():
        raise ValueError("query must not be empty")
    if embedder is None and not re.search(r"\w+", query, flags=re.UNICODE):
        raise ValueError("query must contain at least one searchable term")
    filters, parameters = _filters(
        project=project, after=after, before=before, role=role, files=files
    )
    candidate_limit = limit * 4
    keyword_ranking = _keyword_ranking(
        connection, query, filters, parameters, candidate_limit
    )
    semantic_ranking = (
        _semantic_ranking(
            connection, query, embedder, filters, parameters, candidate_limit
        )
        if embedder is not None
        else []
    )
    fused = _fuse_rankings(keyword_ranking, semantic_ranking)
    if not fused:
        rows = []
    else:
        placeholders = ",".join("?" for _ in fused)
        fetched = connection.execute(
            "SELECT m.id, m.session_id, s.project, m.timestamp, m.role, m.text "
            "FROM messages m JOIN sessions s ON s.id = m.session_id "
            f"WHERE m.id IN ({placeholders})",
            [message_id for message_id, _ in fused],
        ).fetchall()
        by_id = {row["id"]: row for row in fetched}
        rows = [(by_id[message_id], score) for message_id, score in fused]
    results: list[SearchResult] = []
    seen_text: set[str] = set()
    for row, score in rows:
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
                "score": round(score, 6),
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
