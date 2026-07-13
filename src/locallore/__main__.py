from __future__ import annotations

import argparse
import fcntl
import logging
import sqlite3
import sys
from contextlib import contextmanager
from pathlib import Path

from .config import Settings
from .db import connect, migrate
from .doctor import DoctorError, run_doctor
from .embeddings import FastEmbedder, embed_pending_messages
from .importer import import_sessions
from .mcp_server import run_server
from .preferences import configure_history, get_history_setting, history_cutoff
from .status import get_status


def embedding_progress(completed: int, total: int, *, width: int = 30) -> str:
    ratio = 1.0 if total == 0 else min(1.0, completed / total)
    filled = round(width * ratio)
    bar = "#" * filled + "-" * (width - filled)
    return f"Embedding messages [{bar}] {completed}/{total} ({ratio:.0%})"


@contextmanager
def _index_lock(database_path: Path):
    lock_path = database_path.with_suffix(database_path.suffix + ".index.lock")
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with lock_path.open("w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(lock, fcntl.LOCK_UN)


def index(settings: Settings) -> None:
    with _index_lock(settings.database_path):
        _index_locked(settings)


def _index_locked(settings: Settings) -> None:
    connection = connect(settings.database_path)
    try:
        migrate(connection)
        if get_history_setting(connection) is None:
            raise ValueError(
                "history window is not configured; run /locallore:setup first"
            )
        print(
            "Refreshing LocalLore index. On the first run, embedding existing "
            "session history can take several minutes.",
            file=sys.stderr,
        )
        result = import_sessions(
            connection,
            settings.sessions_path,
            history_after=history_cutoff(connection),
        )
        embedder = FastEmbedder(
            settings.embedding_model,
            settings.model_path,
            settings.embedding_dimension,
        )
        embedded = embed_pending_messages(
            connection,
            embedder,
            batch_size=settings.embedding_batch_size,
            on_progress=lambda completed, total: print(
                embedding_progress(completed, total),
                file=sys.stderr,
                flush=True,
            ),
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
    parser.add_argument("command", choices=("mcp", "index", "doctor", "configure"))
    parser.add_argument(
        "history",
        nargs="?",
        help="history preset for configure",
    )
    args = parser.parse_args()
    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)s %(name)s: %(message)s",
        stream=sys.stderr,
    )
    try:
        settings = Settings.from_env()
        if args.command == "mcp":
            connection = connect(settings.database_path)
            try:
                migrate(connection)
                configured = get_history_setting(connection) is not None
            finally:
                connection.close()
            if configured:
                index(settings)
            else:
                print(
                    "LocalLore needs first-run setup. Run /locallore:setup to "
                    "choose how much history to index.",
                    file=sys.stderr,
                )
            run_server()
        elif args.command == "index":
            index(settings)
        elif args.command == "doctor":
            report = run_doctor(settings)
            for check in report.checks:
                print(f"ok: {check}", file=sys.stderr)
            status = get_status(settings.database_path)
            print(
                f"LocalLore ready (schema version {status['schema_version']})",
                file=sys.stderr,
            )
        else:
            if args.history is None:
                parser.error("configure requires a history preset")
            connection = connect(settings.database_path)
            try:
                migrate(connection)
                cutoff = configure_history(connection, args.history)
            finally:
                connection.close()
            print(cutoff)
    except (DoctorError, OSError, sqlite3.Error, ValueError) as exc:
        logging.getLogger(__name__).error("LocalLore startup failed: %s", exc)
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()
