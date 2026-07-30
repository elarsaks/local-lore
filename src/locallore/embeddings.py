from __future__ import annotations

import hashlib
import sqlite3
from collections.abc import Sequence
from pathlib import Path
from typing import Protocol, cast

import numpy as np
from numpy.typing import NDArray

MAX_EMBEDDING_CHARS = 8000
MODEL_CHECKSUM_FILE = ".locallore-model.sha256"
FloatArray = NDArray[np.float32]


class Embedder(Protocol):
    @property
    def model_id(self) -> str: ...

    @property
    def dimension(self) -> int: ...

    def encode(self, texts: Sequence[str]) -> FloatArray: ...

    def encode_query(self, query: str) -> FloatArray: ...


def encode_vector(vector: FloatArray) -> bytes:
    return np.asarray(vector, dtype="<f4").tobytes(order="C")


def decode_vector(value: bytes, dimension: int) -> FloatArray:
    vector = np.frombuffer(value, dtype="<f4")
    if vector.size != dimension:
        raise ValueError(
            f"stored vector has dimension {vector.size}, expected {dimension}"
        )
    return vector


def _directory_checksum(path: Path) -> str:
    checksum_path = path / MODEL_CHECKSUM_FILE
    if checksum_path.is_file():
        checksum = checksum_path.read_text().strip().lower()
        if len(checksum) != 64 or any(
            character not in "0123456789abcdef" for character in checksum
        ):
            raise ValueError(f"invalid model checksum in {checksum_path}")
        return checksum
    digest = hashlib.sha256()
    files = sorted(
        item for item in path.rglob("*") if item.is_file() and item != checksum_path
    )
    if not files:
        raise FileNotFoundError(f"embedding model assets not found in {path}")
    for item in files:
        digest.update(str(item.relative_to(path)).encode())
        with item.open("rb") as handle:
            while chunk := handle.read(1024 * 1024):
                digest.update(chunk)
    return digest.hexdigest()


def embedding_model_id(model_name: str, cache_dir: Path) -> str:
    return f"{model_name}@sha256:{_directory_checksum(cache_dir)}"


class FastEmbedder:
    def __init__(
        self,
        model_name: str,
        cache_dir: Path,
        dimension: int,
        *,
        model_id: str | None = None,
    ) -> None:
        from fastembed import TextEmbedding

        self._dimension = dimension
        self._model_id = model_id or embedding_model_id(model_name, cache_dir)
        self._model = TextEmbedding(
            model_name=model_name,
            cache_dir=str(cache_dir),
            local_files_only=True,
        )

    @property
    def model_id(self) -> str:
        return self._model_id

    @property
    def dimension(self) -> int:
        return self._dimension

    def encode(self, texts: Sequence[str]) -> FloatArray:
        if not texts:
            return np.empty((0, self.dimension), dtype=np.float32)
        vectors = np.asarray(list(self._model.embed(list(texts))), dtype=np.float32)
        if vectors.ndim != 2 or vectors.shape[1] != self.dimension:
            raise ValueError(
                f"model returned shape {vectors.shape}, expected (*, {self.dimension})"
            )
        norms = np.linalg.norm(vectors, axis=1, keepdims=True)
        if np.any(norms == 0):
            raise ValueError("embedding model returned a zero-length vector")
        return cast(FloatArray, vectors / norms)

    def encode_query(self, query: str) -> FloatArray:
        vectors = np.asarray(list(self._model.query_embed(query)), dtype=np.float32)
        if vectors.shape != (1, self.dimension):
            raise ValueError(
                f"model returned shape {vectors.shape}, expected (1, {self.dimension})"
            )
        norm = np.linalg.norm(vectors[0])
        if norm == 0:
            raise ValueError("embedding model returned a zero-length query vector")
        return cast(FloatArray, vectors[0] / norm)


def has_pending_messages(
    connection: sqlite3.Connection,
    model_id: str,
    dimension: int,
) -> bool:
    row = connection.execute(
        "SELECT EXISTS("
        "SELECT 1 FROM messages m "
        "LEFT JOIN embeddings e ON e.message_id = m.id "
        "WHERE m.role IN ('user', 'assistant') AND length(trim(m.text)) >= 3 "
        "AND length(m.text) <= ? "
        "AND (e.message_id IS NULL OR e.model_id != ? OR e.dimension != ? "
        "OR e.content_hash != m.content_hash)"
        ")",
        (MAX_EMBEDDING_CHARS, model_id, dimension),
    ).fetchone()
    return bool(row[0])


def embed_pending_messages(
    connection: sqlite3.Connection,
    embedder: Embedder,
    *,
    batch_size: int = 64,
) -> int:
    if batch_size < 1:
        raise ValueError("embedding batch size must be positive")
    rows = connection.execute(
        "SELECT m.id, m.text, m.content_hash FROM messages m "
        "LEFT JOIN embeddings e ON e.message_id = m.id "
        "WHERE m.role IN ('user', 'assistant') AND length(trim(m.text)) >= 3 "
        "AND length(m.text) <= ? "
        "AND (e.message_id IS NULL OR e.model_id != ? OR e.dimension != ? "
        "OR e.content_hash != m.content_hash) ORDER BY m.rowid",
        (MAX_EMBEDDING_CHARS, embedder.model_id, embedder.dimension),
    ).fetchall()
    embedded = 0
    for offset in range(0, len(rows), batch_size):
        batch = rows[offset : offset + batch_size]
        vectors = embedder.encode([row["text"] for row in batch])
        if vectors.shape != (len(batch), embedder.dimension):
            raise ValueError("embedder returned an unexpected batch shape")
        with connection:
            for row, vector in zip(batch, vectors, strict=True):
                connection.execute(
                    "INSERT INTO embeddings(message_id, model_id, dimension, content_hash, vector) "
                    "VALUES (?, ?, ?, ?, ?) ON CONFLICT(message_id) DO UPDATE SET "
                    "model_id=excluded.model_id, dimension=excluded.dimension, "
                    "content_hash=excluded.content_hash, vector=excluded.vector",
                    (
                        row["id"],
                        embedder.model_id,
                        embedder.dimension,
                        row["content_hash"],
                        encode_vector(vector),
                    ),
                )
        embedded += len(batch)
    return embedded
