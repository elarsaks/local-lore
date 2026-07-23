from __future__ import annotations

import argparse
import logging
import sqlite3
import sys

from .config import Settings
from .db import connect, migrate
from .doctor import DoctorError, run_doctor
from .embeddings import FastEmbedder, embed_pending_messages
from .importer import import_sessions
from .locking import acquire_index_lock
from .mcp_server import run_server
from .status import get_status


def index(settings: Settings) -> None:
    with acquire_index_lock(settings.database_path):
        connection = connect(settings.database_path)
        try:
            migrate(connection)
            result = import_sessions(connection, settings.sessions_path)
            embedder = FastEmbedder(
                settings.embedding_model,
                settings.model_path,
                settings.embedding_dimension,
            )
            embedded = embed_pending_messages(
                connection, embedder, batch_size=settings.embedding_batch_size
            )
            print(
                f"Indexed {result.messages_added} messages "
                f"from {result.files_changed} changed files; "
                f"embedded {embedded} messages",
                file=sys.stderr,
            )
        finally:
            connection.close()


def main() -> None:
    parser = argparse.ArgumentParser(prog="locallore")
    parser.add_argument("command", choices=("mcp", "index", "doctor"))
    args = parser.parse_args()
    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)s %(name)s: %(message)s",
        stream=sys.stderr,
    )
    try:
        settings = Settings.from_env()
        if args.command == "mcp":
            index(settings)
            run_server()
        elif args.command == "index":
            index(settings)
        else:
            report = run_doctor(settings)
            for check in report.checks:
                print(f"ok: {check}", file=sys.stderr)
            status = get_status(settings.database_path)
            print(
                f"LocalLore ready (schema version {status['schema_version']})",
                file=sys.stderr,
            )
    except (DoctorError, OSError, sqlite3.Error, ValueError) as exc:
        logging.getLogger(__name__).error("LocalLore startup failed: %s", exc)
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()
