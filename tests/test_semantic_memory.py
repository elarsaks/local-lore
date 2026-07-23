from __future__ import annotations

import hashlib
from pathlib import Path
from types import MappingProxyType

import numpy as np
import pytest

from locallore.db import connect, migrate
from locallore.embeddings import (
    MAX_EMBEDDING_CHARS,
    MODEL_CHECKSUM_FILE,
    _directory_checksum,
    decode_vector,
    embed_pending_messages,
    embedding_model_id,
    encode_vector,
    has_pending_messages,
)
from locallore.search import _fuse_rankings, search_messages
from locallore.status import get_status


class FakeEmbedder:
    def __init__(
        self,
        vectors: dict[str, list[float]],
        *,
        model_id: str = "fake-v1",
    ) -> None:
        self.vectors = MappingProxyType(vectors)
        self._model_id = model_id
        self.calls: list[list[str]] = []

    @property
    def model_id(self) -> str:
        return self._model_id

    @property
    def dimension(self) -> int:
        return 3

    def encode(self, texts):
        self.calls.append(list(texts))
        vectors = np.asarray([self.vectors[text] for text in texts], dtype=np.float32)
        norms = np.linalg.norm(vectors, axis=1, keepdims=True)
        return vectors / norms

    def encode_query(self, query: str):
        return self.encode([query])[0]


def semantic_database(tmp_path: Path):
    connection = connect(tmp_path / "semantic.db")
    migrate(connection)
    connection.execute(
        "INSERT INTO sessions(id, source_path, project, imported_at) VALUES (?, ?, ?, ?)",
        ("session", "fixture.jsonl", "alpha", "2026-01-01T00:00:00Z"),
    )
    messages = (
        ("login", 1, "Users cannot sign in after their credentials expire"),
        ("database", 2, "The schema migration is idempotent"),
    )
    for message_id, line, text in messages:
        connection.execute(
            "INSERT INTO messages(id, session_id, source_line, role, raw_type, text, content_hash) "
            "VALUES (?, 'session', ?, 'assistant', 'assistant', ?, ?)",
            (message_id, line, text, hashlib.sha256(text.encode()).hexdigest()),
        )
    connection.commit()
    return connection


def test_float32_vector_round_trip_is_little_endian() -> None:
    original = np.asarray([0.25, -0.5, 1.0], dtype=np.float32)
    stored = encode_vector(original)
    restored = decode_vector(stored, 3)
    assert restored.dtype == np.dtype("<f4")
    np.testing.assert_array_equal(restored, original)


def test_embedding_is_batched_idempotent_and_model_aware(tmp_path: Path) -> None:
    connection = semantic_database(tmp_path)
    texts = {
        "Users cannot sign in after their credentials expire": [1, 0, 0],
        "The schema migration is idempotent": [0, 1, 0],
    }
    first = FakeEmbedder(texts)

    assert embed_pending_messages(connection, first, batch_size=1) == 2
    assert len(first.calls) == 2
    assert embed_pending_messages(connection, first, batch_size=1) == 0

    replacement = FakeEmbedder(texts, model_id="fake-v2")
    assert embed_pending_messages(connection, replacement, batch_size=8) == 2
    assert connection.execute(
        "SELECT count(*) FROM embeddings WHERE model_id = 'fake-v2'"
    ).fetchone()[0] == 2
    status = get_status(tmp_path / "semantic.db")
    assert status["embedded_messages"] == 2
    assert status["embedding_model_id"] == "fake-v2"


def test_pending_check_uses_model_and_content_identity(tmp_path: Path) -> None:
    connection = semantic_database(tmp_path)

    assert has_pending_messages(connection, "fake-v1", 3)
    embedder = FakeEmbedder(
        {
            "Users cannot sign in after their credentials expire": [1, 0, 0],
            "The schema migration is idempotent": [0, 1, 0],
        }
    )
    embed_pending_messages(connection, embedder)
    assert not has_pending_messages(connection, "fake-v1", 3)
    assert has_pending_messages(connection, "fake-v2", 3)
    assert has_pending_messages(connection, "fake-v1", 4)


def test_precomputed_model_checksum_avoids_runtime_asset_reads(
    tmp_path: Path, monkeypatch,
) -> None:
    model_path = tmp_path / "model"
    model_path.mkdir()
    asset = model_path / "model.onnx"
    asset.write_bytes(b"model assets")
    checksum = _directory_checksum(model_path)
    (model_path / MODEL_CHECKSUM_FILE).write_text(f"{checksum}\n")

    original_open = Path.open

    def guarded_open(path: Path, *args, **kwargs):
        if path == asset:
            raise AssertionError(
                "model asset was read despite the checksum file"
            )
        return original_open(path, *args, **kwargs)

    monkeypatch.setattr(Path, "open", guarded_open)

    assert embedding_model_id("fixture", model_path) == (
        f"fixture@sha256:{checksum}"
    )


def test_invalid_precomputed_model_checksum_is_rejected(tmp_path: Path) -> None:
    model_path = tmp_path / "model"
    model_path.mkdir()
    (model_path / MODEL_CHECKSUM_FILE).write_text("not-a-checksum\n")

    with pytest.raises(ValueError, match="invalid model checksum"):
        embedding_model_id("fixture", model_path)


def test_large_raw_content_is_not_embedded(tmp_path: Path) -> None:
    connection = semantic_database(tmp_path)
    large_text = "x" * (MAX_EMBEDDING_CHARS + 1)
    connection.execute(
        "UPDATE messages SET text = ?, content_hash = ? WHERE id = 'login'",
        (large_text, hashlib.sha256(large_text.encode()).hexdigest()),
    )
    embedder = FakeEmbedder(
        {"The schema migration is idempotent": [0, 1, 0]}
    )

    assert embed_pending_messages(connection, embedder) == 1
    assert connection.execute(
        "SELECT message_id FROM embeddings"
    ).fetchone()[0] == "database"


def test_semantic_query_retrieves_paraphrase_without_keyword_overlap(
    tmp_path: Path,
) -> None:
    connection = semantic_database(tmp_path)
    query = "authentication problem"
    vectors = {
        "Users cannot sign in after their credentials expire": [1, 0, 0],
        "The schema migration is idempotent": [0, 1, 0],
        query: [0.99, 0.01, 0],
    }
    embedder = FakeEmbedder(vectors)
    embed_pending_messages(connection, embedder)

    response = search_messages(connection, query, embedder=embedder)

    assert response["results"][0]["message_id"] == "login"
    assert search_messages(connection, query)["results"] == []


def test_reciprocal_rank_fusion_rewards_agreement() -> None:
    fused = _fuse_rankings(["keyword", "both"], ["both", "semantic"])
    assert fused[0][0] == "both"
