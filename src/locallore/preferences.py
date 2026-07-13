from __future__ import annotations

import sqlite3
from datetime import UTC, datetime, timedelta

HISTORY_PRESETS = {
    "today": 0,
    "1_week": 7,
    "1_month": 30,
    "3_months": 90,
    "1_year": 365,
    "all": None,
}


def get_history_setting(connection: sqlite3.Connection) -> str | None:
    row = connection.execute(
        "SELECT value FROM settings WHERE key = 'history_after'"
    ).fetchone()
    return row[0] if row else None


def configure_history(
    connection: sqlite3.Connection,
    preset: str,
    *,
    now: datetime | None = None,
) -> str:
    if preset not in HISTORY_PRESETS:
        raise ValueError(
            "history must be one of: today, 1_week, 1_month, 3_months, 1_year, all"
        )
    days = HISTORY_PRESETS[preset]
    current = now or datetime.now(UTC)
    if days is None:
        value = "all"
    elif days == 0:
        value = current.replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
    else:
        value = (current - timedelta(days=days)).isoformat()
    previous = get_history_setting(connection)
    with connection:
        connection.execute(
            "INSERT INTO settings(key, value, updated_at) VALUES "
            "('history_after', ?, ?) ON CONFLICT(key) DO UPDATE SET "
            "value=excluded.value, updated_at=excluded.updated_at",
            (value, current.isoformat()),
        )
        if previous != value:
            connection.execute("DELETE FROM sessions")
            connection.execute("DELETE FROM import_files")
    return value


def history_cutoff(connection: sqlite3.Connection) -> str | None:
    value = get_history_setting(connection)
    return None if value in (None, "all") else value
