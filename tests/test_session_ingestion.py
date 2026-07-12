from __future__ import annotations

import shutil
from pathlib import Path

from locallore.db import connect, migrate
from locallore.discovery import discover
from locallore.importer import import_sessions

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
    import_sessions(connection, sessions)
    assert connection.execute("SELECT count(*) FROM messages").fetchone()[0] == 1


def test_outside_session_symlinks_are_ignored(tmp_path: Path) -> None:
    root = tmp_path / "sessions"
    root.mkdir()
    outside = tmp_path / "outside.jsonl"
    outside.write_text("{}\n")
    (root / "linked.jsonl").symlink_to(outside)
    assert discover(root) == []
