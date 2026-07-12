from __future__ import annotations

import hashlib
import time
import tracemalloc
from pathlib import Path

import numpy as np

from locallore.db import connect, migrate
from locallore.embeddings import encode_vector
from locallore.search import search_messages


class FixedEmbedder:
    model_id = "performance-fixture"
    dimension = 32

    def encode_query(self, query: str) -> np.ndarray:
        seed = int.from_bytes(hashlib.sha256(query.encode()).digest()[:8], "little")
        vector = np.random.default_rng(seed).normal(size=self.dimension).astype(np.float32)
        return vector / np.linalg.norm(vector)


def test_hybrid_search_has_bounded_time_and_python_memory(tmp_path: Path) -> None:
    connection = connect(tmp_path / "performance.db")
    migrate(connection)
    connection.execute(
        "INSERT INTO sessions(id, source_path, project, imported_at) VALUES "
        "('session', 'fixture.jsonl', 'performance', '2026-01-01T00:00:00Z')"
    )
    embedder = FixedEmbedder()
    rng = np.random.default_rng(42)
    for index in range(2_000):
        text = f"performance fixture message {index} about offline memory"
        vector = rng.normal(size=embedder.dimension).astype(np.float32)
        vector /= np.linalg.norm(vector)
        message_id = f"message-{index}"
        connection.execute(
            "INSERT INTO messages(id, session_id, source_line, role, raw_type, text, content_hash) "
            "VALUES (?, 'session', ?, 'assistant', 'assistant', ?, ?)",
            (message_id, index + 1, text, hashlib.sha256(text.encode()).hexdigest()),
        )
        connection.execute(
            "INSERT INTO embeddings(message_id, model_id, dimension, content_hash, vector) "
            "VALUES (?, ?, ?, ?, ?)",
            (message_id, embedder.model_id, embedder.dimension, hashlib.sha256(text.encode()).hexdigest(), encode_vector(vector)),
        )
    connection.commit()

    tracemalloc.start()
    started = time.perf_counter()
    for index in range(10):
        response = search_messages(
            connection,
            f"offline memory fixture {index}",
            embedder=embedder,
            limit=8,
        )
        assert len(response["results"]) == 8
    elapsed = time.perf_counter() - started
    _, peak_bytes = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    assert elapsed < 5.0, f"10 searches took {elapsed:.3f}s"
    assert peak_bytes < 64 * 1024 * 1024, f"peak allocation was {peak_bytes / 1024 / 1024:.1f} MiB"
