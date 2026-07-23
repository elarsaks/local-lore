from __future__ import annotations

import argparse
import json
import shutil
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from locallore.db import connect, migrate
from locallore.discovery import discover
from locallore.embeddings import embed_pending_messages
from locallore.importer import import_sessions


@dataclass(frozen=True)
class FixtureEmbedder:
    model_id: str = "benchmark-v1"
    dimension: int = 32

    def encode(self, texts: list[str]) -> np.ndarray:
        vectors = np.ones((len(texts), self.dimension), dtype=np.float32)
        return vectors / np.linalg.norm(vectors, axis=1, keepdims=True)


def _record(file_index: int, line_index: int) -> str:
    return json.dumps(
        {
            "type": "assistant",
            "sessionId": f"session-{file_index}",
            "uuid": f"message-{file_index}-{line_index}",
            "timestamp": "2026-01-01T00:00:00Z",
            "message": {
                "role": "assistant",
                "content": f"offline indexing benchmark message {file_index} {line_index}",
            },
        },
        separators=(",", ":"),
    )


def _write_fixture(root: Path, files: int, messages_per_file: int) -> None:
    root.mkdir()
    for file_index in range(files):
        project = root / f"project-{file_index % 20}"
        project.mkdir(exist_ok=True)
        source = project / f"session-{file_index}.jsonl"
        source.write_text(
            "".join(
                f"{_record(file_index, line_index)}\n"
                for line_index in range(messages_per_file)
            )
        )


def _timed(label: str, operation) -> float:
    started = time.perf_counter()
    result = operation()
    elapsed = time.perf_counter() - started
    print(f"{label:24} {elapsed:9.4f}s  {result}")
    return elapsed


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--files", type=int, default=1_000)
    parser.add_argument("--messages-per-file", type=int, default=10)
    parser.add_argument("--changed-files", type=int, default=100)
    parser.add_argument("--keep", type=Path)
    parser.add_argument(
        "--append-to",
        type=Path,
        help="append one record to existing fixture files, then exit",
    )
    args = parser.parse_args()

    if args.append_to:
        for file_index in range(min(args.changed_files, args.files)):
            source = (
                args.append_to
                / f"project-{file_index % 20}"
                / f"session-{file_index}.jsonl"
            )
            with source.open("a") as handle:
                handle.write(
                    f"{_record(file_index, args.messages_per_file)}\n"
                )
        return

    temporary = Path(tempfile.mkdtemp(prefix="locallore-profile-"))
    sessions = temporary / "sessions"
    database = temporary / "locallore.db"
    try:
        _write_fixture(sessions, args.files, args.messages_per_file)
        connection = connect(database)
        migrate(connection)
        embedder = FixtureEmbedder()

        _timed("discovery", lambda: len(discover(sessions)))
        _timed("initial import", lambda: import_sessions(connection, sessions))
        _timed(
            "initial embedding",
            lambda: embed_pending_messages(connection, embedder),
        )
        _timed("unchanged import", lambda: import_sessions(connection, sessions))
        _timed(
            "unchanged embedding",
            lambda: embed_pending_messages(connection, embedder),
        )

        for file_index in range(min(args.changed_files, args.files)):
            source = (
                sessions
                / f"project-{file_index % 20}"
                / f"session-{file_index}.jsonl"
            )
            with source.open("a") as handle:
                handle.write(
                    f"{_record(file_index, args.messages_per_file)}\n"
                )

        _timed("incremental import", lambda: import_sessions(connection, sessions))
        _timed(
            "incremental embedding",
            lambda: embed_pending_messages(connection, embedder),
        )
        connection.close()
        if args.keep:
            shutil.copytree(temporary, args.keep)
            print(f"fixture copied to {args.keep}")
    finally:
        shutil.rmtree(temporary)


if __name__ == "__main__":
    main()
