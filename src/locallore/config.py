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
    http_host: str = "0.0.0.0"
    http_port: int = 8000
    public_port: int = 8765
    bearer_token: str = ""
    watcher_interval: float = 2.0
    watcher_idle_interval: float = 2.0
    watcher_debounce: float = 0.5
    runtime_version: str = "0.2.0"

    @classmethod
    def from_env(cls) -> Settings:
        return cls(
            database_path=Path(os.environ.get("LOCALLORE_DB", "/data/locallore.db")),
            sessions_path=Path(os.environ.get("LOCALLORE_SESSIONS", "/sessions")),
            model_path=Path(os.environ.get("LOCALLORE_MODEL_PATH", "/models")),
            embedding_model=os.environ.get(
                "LOCALLORE_EMBEDDING_MODEL", "BAAI/bge-small-en-v1.5"
            ),
            embedding_dimension=int(
                os.environ.get("LOCALLORE_EMBEDDING_DIMENSION", "384")
            ),
            embedding_batch_size=int(
                os.environ.get("LOCALLORE_EMBEDDING_BATCH_SIZE", "64")
            ),
            http_host=os.environ.get("LOCALLORE_HTTP_HOST", "0.0.0.0"),
            http_port=int(os.environ.get("LOCALLORE_HTTP_PORT", "8000")),
            public_port=int(os.environ.get("LOCALLORE_PORT", "8765")),
            bearer_token=os.environ.get("LOCALLORE_TOKEN", ""),
            watcher_interval=float(os.environ.get("LOCALLORE_WATCH_INTERVAL", "2")),
            watcher_idle_interval=float(
                os.environ.get("LOCALLORE_IDLE_WATCH_INTERVAL", "2")
            ),
            watcher_debounce=float(os.environ.get("LOCALLORE_WATCH_DEBOUNCE", "0.5")),
            runtime_version=os.environ.get("LOCALLORE_ACTIVE_VERSION", "0.2.0"),
        )
