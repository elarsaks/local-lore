from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class Settings:
    database_path: Path
    sessions_path: Path
    model_path: Path
    embedding_model: str
    embedding_dimension: int
    embedding_batch_size: int

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            database_path=Path(os.environ.get("LOCALLORE_DB", "/data/locallore.db")),
            sessions_path=Path(os.environ.get("LOCALLORE_SESSIONS", "/sessions")),
            model_path=Path(os.environ.get("LOCALLORE_MODEL_PATH", "/models")),
            embedding_model=os.environ.get(
                "LOCALLORE_EMBEDDING_MODEL", "BAAI/bge-small-en-v1.5"
            ),
            embedding_dimension=int(os.environ.get("LOCALLORE_EMBEDDING_DIMENSION", "384")),
            embedding_batch_size=int(os.environ.get("LOCALLORE_EMBEDDING_BATCH_SIZE", "64")),
        )
