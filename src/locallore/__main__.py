from __future__ import annotations

import argparse
import sys

from .config import Settings
from .db import connect, migrate
from .embeddings import FastEmbedder, embed_pending_messages
from .importer import import_sessions
from .mcp_server import run_server
from .status import get_status


def index(settings: Settings) -> None:
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
    settings = Settings.from_env()

    if args.command == "mcp":
        index(settings)
        run_server()
    elif args.command == "index":
        index(settings)
    else:
        status = get_status(settings.database_path)
        print(f"LocalLore ready (schema version {status['schema_version']})", file=sys.stderr)


if __name__ == "__main__":
    main()
