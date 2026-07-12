from __future__ import annotations

import os
import sqlite3
import tempfile
from dataclasses import dataclass
from pathlib import Path

from .config import Settings
from .db import connect, migrate
from .embeddings import FastEmbedder


class DoctorError(RuntimeError):
    """Raised when a runtime prerequisite is unavailable or unsafe."""


@dataclass(frozen=True, slots=True)
class DoctorReport:
    checks: tuple[str, ...]


def _require_directory(path: Path, label: str, *, readable: bool = True) -> None:
    if not path.is_dir():
        raise DoctorError(f"{label} directory does not exist: {path}")
    if readable and not os.access(path, os.R_OK | os.X_OK):
        raise DoctorError(f"{label} directory is not readable: {path}")


def run_doctor(settings: Settings) -> DoctorReport:
    checks: list[str] = []
    _require_directory(settings.sessions_path, "session")
    checks.append("session directory is readable")

    database_parent = settings.database_path.parent
    _require_directory(database_parent, "database", readable=False)
    try:
        with tempfile.NamedTemporaryFile(dir=database_parent):
            pass
    except OSError as exc:
        raise DoctorError(f"database directory is not writable: {database_parent}: {exc}") from exc
    checks.append("database directory is writable")

    connection: sqlite3.Connection | None = None
    try:
        connection = connect(settings.database_path)
        migrate(connection)
        if connection.execute("PRAGMA foreign_keys").fetchone()[0] != 1:
            raise DoctorError("SQLite foreign-key enforcement is disabled")
        connection.execute("SELECT count(*) FROM messages_fts").fetchone()
    except sqlite3.Error as exc:
        raise DoctorError(f"database or FTS5 check failed: {exc}") from exc
    finally:
        if connection is not None:
            connection.close()
    checks.append("database, migrations, foreign keys, and FTS5 are ready")

    _require_directory(settings.model_path, "embedding model")
    try:
        embedder = FastEmbedder(
            settings.embedding_model,
            settings.model_path,
            settings.embedding_dimension,
        )
        vector = embedder.encode_query("LocalLore offline diagnostic")
    except Exception as exc:
        raise DoctorError(f"embedding model check failed: {exc}") from exc
    if vector.shape != (settings.embedding_dimension,):
        raise DoctorError(f"embedding model returned unexpected shape {vector.shape}")
    checks.append("local embedding assets and inference are ready")

    if os.environ.get("LOCALLORE_NETWORK_MODE") != "none":
        raise DoctorError(
            "cannot confirm the offline runtime; run doctor through scripts/doctor.sh"
        )
    checks.append("Compose declares the runtime network disabled")
    return DoctorReport(tuple(checks))
