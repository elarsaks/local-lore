from __future__ import annotations

import shutil
from pathlib import Path

import pytest

import locallore.indexing.importer
from locallore.indexing.discovery import discover
from locallore.indexing.importer import import_sessions
from locallore.storage.db import connect, migrate

FIXTURES = Path(__file__).parent / "fixtures" / "sessions"


def snapshot(connection):
    return {
        "sessions": connection.execute("SELECT id, source_path, project, cwd, started_at FROM sessions ORDER BY id").fetchall(),
        "messages": connection.execute("SELECT id, session_id, source_line, role, timestamp, text, content_hash FROM messages ORDER BY id").fetchall(),
        "checkpoints": connection.execute("SELECT path, identity, size_bytes, offset_bytes, last_line, last_error FROM import_files ORDER BY path").fetchall(),
    }


def test_unchanged_sessions_are_not_reimported(tmp_path: Path) -> None:
    sessions = tmp_path / "sessions"
    shutil.copytree(FIXTURES, sessions)
    connection = connect(tmp_path / "db.sqlite")
    migrate(connection)
    migrate(connection)
    first = import_sessions(connection, sessions)
    before = snapshot(connection)
    second = import_sessions(connection, sessions)
    assert first.messages_added == 2
    assert first.errors == 1
    assert second.files_changed == 0
    assert snapshot(connection) == before


def test_new_complete_records_are_imported_on_refresh(tmp_path: Path) -> None:
    sessions = tmp_path / "sessions"
    shutil.copytree(FIXTURES, sessions)
    connection = connect(tmp_path / "db.sqlite")
    migrate(connection)
    import_sessions(connection, sessions)
    source = sessions / "project-a" / "session-1.jsonl"
    with source.open("a") as handle:
        handle.write('{"type":"user","sessionId":"session-1","uuid":"message-3","message":{"role":"user","content":"new message"}}\n')
    result = import_sessions(connection, sessions)
    assert result.messages_added == 1
    assert connection.execute("SELECT count(*) FROM messages").fetchone()[0] == 3


def test_incomplete_trailing_record_is_deferred_until_complete(tmp_path: Path) -> None:
    sessions = tmp_path / "sessions"
    sessions.mkdir()
    source = sessions / "session.jsonl"
    source.write_text(
        '{"sessionId":"s","uuid":"m","message":{"role":"user","content":"held"}}'
    )
    connection = connect(tmp_path / "db.sqlite")
    migrate(connection)
    assert import_sessions(connection, sessions).messages_added == 0
    assert connection.execute(
        "SELECT offset_bytes FROM import_files"
    ).fetchone()[0] == 0
    with source.open("a") as handle:
        handle.write("\n")
    assert import_sessions(connection, sessions).messages_added == 1


def test_replaced_or_truncated_session_is_rebuilt(tmp_path: Path) -> None:
    sessions = tmp_path / "sessions"
    shutil.copytree(FIXTURES, sessions)
    connection = connect(tmp_path / "db.sqlite")
    migrate(connection)
    import_sessions(connection, sessions)
    source = sessions / "project-a" / "session-1.jsonl"
    source.write_text(source.read_text().splitlines()[0] + "\n")
    result = import_sessions(connection, sessions)
    assert connection.execute("SELECT count(*) FROM messages").fetchone()[0] == 1
    assert result.messages_removed == 2


def test_deleted_source_cascades_all_derived_rows(tmp_path: Path) -> None:
    sessions = tmp_path / "sessions"
    shutil.copytree(FIXTURES, sessions)
    connection = connect(tmp_path / "db.sqlite")
    migrate(connection)
    import_sessions(connection, sessions)
    connection.execute(
        "INSERT INTO file_operations(message_id, path, operation) "
        "VALUES ('message-1', 'src/example.py', 'edit')"
    )
    connection.execute(
        "INSERT INTO embeddings(message_id, model_id, dimension, content_hash, vector) "
        "SELECT id, 'fixture', 1, content_hash, ? FROM messages WHERE id = 'message-1'",
        (b"\x00\x00\x80?",),
    )
    connection.commit()

    (sessions / "project-a" / "session-1.jsonl").unlink()
    result = import_sessions(connection, sessions)

    assert result.files_removed == 1
    assert result.messages_removed == 2
    assert connection.execute("SELECT count(*) FROM sessions").fetchone()[0] == 0
    assert connection.execute("SELECT count(*) FROM messages").fetchone()[0] == 0
    assert connection.execute("SELECT count(*) FROM messages_fts").fetchone()[0] == 0
    assert connection.execute("SELECT count(*) FROM file_operations").fetchone()[0] == 0
    assert connection.execute("SELECT count(*) FROM embeddings").fetchone()[0] == 0
    assert connection.execute("SELECT count(*) FROM import_files").fetchone()[0] == 0


def test_outside_session_symlinks_are_ignored(tmp_path: Path) -> None:
    root = tmp_path / "sessions"
    root.mkdir()
    outside = tmp_path / "outside.jsonl"
    outside.write_text("{}\n")
    (root / "linked.jsonl").symlink_to(outside)
    assert discover(root) == []


def test_multi_file_import_is_atomic(tmp_path: Path, monkeypatch) -> None:
    sessions = tmp_path / "sessions"
    sessions.mkdir()
    record = (
        '{"sessionId":"%s","uuid":"%s","message":'
        '{"role":"user","content":"message"}}\n'
    )
    (sessions / "first.jsonl").write_text(record % ("first", "first-message"))
    (sessions / "second.jsonl").write_text(
        record % ("second", "second-message")
    )
    connection = connect(tmp_path / "db.sqlite")
    migrate(connection)
    original = locallore.indexing.importer._import_file
    calls = 0

    def fail_second_file(connection, source, checkpoint):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise RuntimeError("simulated import failure")
        return original(connection, source, checkpoint)

    monkeypatch.setattr(
        locallore.indexing.importer, "_import_file", fail_second_file
    )

    with pytest.raises(RuntimeError, match="simulated import failure"):
        import_sessions(connection, sessions)
    assert connection.execute("SELECT count(*) FROM messages").fetchone()[0] == 0
    assert (
        connection.execute("SELECT count(*) FROM import_files").fetchone()[0]
        == 0
    )
