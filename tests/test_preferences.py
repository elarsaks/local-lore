from __future__ import annotations

from datetime import UTC, datetime

import pytest

from locallore.db import connect, migrate
from locallore.preferences import configure_history, get_history_setting, history_cutoff


def test_history_preset_is_stored_as_absolute_cutoff(tmp_path) -> None:
    connection = connect(tmp_path / "db.sqlite")
    migrate(connection)

    value = configure_history(
        connection, "1_month", now=datetime(2026, 7, 12, tzinfo=UTC)
    )

    assert value == "2026-06-12T00:00:00+00:00"
    assert get_history_setting(connection) == value
    assert history_cutoff(connection) == value


def test_all_history_has_no_cutoff(tmp_path) -> None:
    connection = connect(tmp_path / "db.sqlite")
    migrate(connection)
    configure_history(connection, "all")
    assert history_cutoff(connection) is None


def test_today_starts_at_utc_midnight(tmp_path) -> None:
    connection = connect(tmp_path / "db.sqlite")
    migrate(connection)

    value = configure_history(
        connection, "today", now=datetime(2026, 7, 13, 16, 42, 31, tzinfo=UTC)
    )

    assert value == "2026-07-13T00:00:00+00:00"
    assert history_cutoff(connection) == value


def test_changing_history_rebuilds_derived_index(tmp_path) -> None:
    connection = connect(tmp_path / "db.sqlite")
    migrate(connection)
    configure_history(connection, "1_week")
    connection.execute(
        "INSERT INTO import_files(path, size_bytes, mtime_ns, updated_at) "
        "VALUES ('file', 1, 1, 'now')"
    )
    connection.execute(
        "INSERT INTO sessions(id, source_path, imported_at) VALUES ('s', 'file', 'now')"
    )
    connection.commit()

    configure_history(connection, "1_year")

    assert connection.execute("SELECT count(*) FROM sessions").fetchone()[0] == 0
    assert connection.execute("SELECT count(*) FROM import_files").fetchone()[0] == 0


def test_first_configuration_rebuilds_an_existing_legacy_index(tmp_path) -> None:
    connection = connect(tmp_path / "db.sqlite")
    migrate(connection)
    connection.execute(
        "INSERT INTO import_files(path, size_bytes, mtime_ns, updated_at) "
        "VALUES ('file', 1, 1, 'now')"
    )
    connection.execute(
        "INSERT INTO sessions(id, source_path, imported_at) VALUES ('s', 'file', 'now')"
    )
    connection.commit()

    configure_history(connection, "1_month")

    assert connection.execute("SELECT count(*) FROM sessions").fetchone()[0] == 0
    assert connection.execute("SELECT count(*) FROM import_files").fetchone()[0] == 0


def test_invalid_history_preset_is_rejected(tmp_path) -> None:
    connection = connect(tmp_path / "db.sqlite")
    migrate(connection)
    with pytest.raises(ValueError, match="history must be one of"):
        configure_history(connection, "forever")
