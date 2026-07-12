from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import TypedDict

from .db import SCHEMA_VERSION


class Status(TypedDict):
    schema_version: int
    last_refresh: str | None
    sessions: int
    messages: int
    embedded_messages: int
    embedding_model_id: str | None
    import_errors: list[str]
    runtime_network: str


def get_status(database_path: Path | None = None) -> Status:
    sessions = messages = embedded_messages = 0
    embedding_model_id = None
    errors: list[str] = []
    last_refresh = None
    if database_path is not None and database_path.exists():
        connection = sqlite3.connect(database_path)
        sessions = connection.execute("SELECT count(*) FROM sessions").fetchone()[0]
        messages = connection.execute("SELECT count(*) FROM messages").fetchone()[0]
        embedded_messages = connection.execute(
            "SELECT count(*) FROM embeddings"
        ).fetchone()[0]
        model = connection.execute(
            "SELECT model_id FROM embeddings GROUP BY model_id ORDER BY count(*) DESC LIMIT 1"
        ).fetchone()
        embedding_model_id = model[0] if model else None
        errors = [
            row[0]
            for row in connection.execute(
                "SELECT path FROM import_files WHERE last_error IS NOT NULL"
            )
        ]
        last_refresh = connection.execute(
            "SELECT max(updated_at) FROM import_files"
        ).fetchone()[0]
        connection.close()
    return {
        "schema_version": SCHEMA_VERSION,
        "last_refresh": last_refresh,
        "sessions": sessions,
        "messages": messages,
        "embedded_messages": embedded_messages,
        "embedding_model_id": embedding_model_id,
        "import_errors": errors,
        "runtime_network": "disabled by Docker Compose",
    }
