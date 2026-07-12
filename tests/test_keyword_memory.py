from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from locallore.db import connect, migrate
from locallore.importer import import_sessions
from locallore.search import EXCERPT_LENGTH, get_context, search_messages


def indexed_database(tmp_path: Path):
    sessions = tmp_path / "sessions" / "alpha"
    sessions.mkdir(parents=True)
    (sessions / "history.jsonl").write_text(
        '\n'.join(
            (
                '{"type":"user","sessionId":"s1","uuid":"m1","timestamp":"2026-01-01T10:00:00Z","project":"alpha","message":{"role":"user","content":"Why remove the HTTP transport?"}}',
                '{"type":"assistant","sessionId":"s1","uuid":"m2","timestamp":"2026-01-01T10:01:00Z","project":"alpha","message":{"role":"assistant","content":[{"type":"text","text":"We removed the HTTP transport to keep the runtime offline."},{"type":"tool_use","name":"Edit","input":{"file_path":"compose.yaml"}}]}}',
                '{"type":"user","sessionId":"s1","uuid":"m3","timestamp":"2026-01-01T10:02:00Z","project":"alpha","message":{"role":"user","content":"Unrelated deployment note"}}',
                '{"type":"assistant","sessionId":"s2","uuid":"m4","timestamp":"2025-01-01T10:00:00Z","project":"beta","message":{"role":"assistant","content":"HTTP transport remains enabled here."}}',
            )
        )
        + '\n'
    )
    connection = connect(tmp_path / "locallore.db")
    migrate(connection)
    import_sessions(connection, tmp_path / "sessions")
    return connection


def test_fts_returns_ranked_metadata(tmp_path: Path) -> None:
    connection = indexed_database(tmp_path)
    response = search_messages(connection, "removed HTTP transport", project="alpha")
    assert response["results"][0]["message_id"] == "m2"
    assert response["results"][0]["files"] == ["compose.yaml"]
    assert response["results"][0]["score"] > 0
    assert response["index"]["refresh_errors"] == 0


def test_search_applies_structured_filters(tmp_path: Path) -> None:
    connection = indexed_database(tmp_path)
    response = search_messages(
        connection,
        "HTTP transport",
        after="2026-01-01",
        before="2026-02-01",
        role="assistant",
        files=["compose.yaml"],
    )
    assert [result["message_id"] for result in response["results"]] == ["m2"]


def test_search_bounds_excerpts(tmp_path: Path) -> None:
    connection = indexed_database(tmp_path)
    connection.execute("UPDATE messages SET text = ? WHERE id = 'm2'", ("HTTP " * 1000,))
    response = search_messages(connection, "HTTP", limit=1000)
    assert len(response["results"][0]["excerpt"]) == EXCERPT_LENGTH


def test_context_returns_surrounding_messages(tmp_path: Path) -> None:
    connection = indexed_database(tmp_path)
    context = get_context(connection, "s1", "m2", before=1, after=1)
    assert [message["message_id"] for message in context["messages"]] == [
        "m1",
        "m2",
        "m3",
    ]


def test_search_validates_inputs(tmp_path: Path) -> None:
    connection = indexed_database(tmp_path)
    with pytest.raises(ValueError, match="searchable term"):
        search_messages(connection, "---")
    with pytest.raises(ValueError, match="role"):
        search_messages(connection, "HTTP", role="system")


def test_rebuilding_source_removes_stale_fts_rows(tmp_path: Path) -> None:
    connection = indexed_database(tmp_path)
    source = tmp_path / "sessions" / "alpha" / "history.jsonl"
    source.write_text(
        '{"sessionId":"s1","uuid":"replacement","message":{"role":"user","content":"replacement text"}}\n'
    )
    import_sessions(connection, tmp_path / "sessions")
    assert search_messages(connection, "HTTP")["results"] == []
    assert search_messages(connection, "replacement")["results"][0]["message_id"] == "replacement"


def test_file_operation_uses_existing_id_for_logically_duplicate_message(
    tmp_path: Path,
) -> None:
    sessions = tmp_path / "sessions"
    sessions.mkdir()
    text = "Tool use: Edit"
    (sessions / "history.jsonl").write_text(
        '{"sessionId":"s1","uuid":"new-id","message":{"role":"assistant",'
        '"content":[{"type":"tool_use","name":"Edit",'
        '"input":{"file_path":"compose.yaml"}}]}}\n'
    )
    connection = connect(tmp_path / "locallore.db")
    migrate(connection)
    connection.execute(
        "INSERT INTO sessions(id, source_path, imported_at) VALUES (?, ?, ?)",
        ("s1", "history.jsonl", "2026-01-01T00:00:00Z"),
    )
    connection.execute(
        "INSERT INTO messages(id, session_id, source_line, role, raw_type, text, content_hash) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        (
            "legacy-id",
            "s1",
            1,
            "assistant",
            "assistant",
            text,
            hashlib.sha256(text.encode()).hexdigest(),
        ),
    )
    connection.commit()

    import_sessions(connection, sessions)

    operation = connection.execute(
        "SELECT message_id, path FROM file_operations"
    ).fetchone()
    assert tuple(operation) == ("legacy-id", "compose.yaml")
