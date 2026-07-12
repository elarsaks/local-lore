from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class Settings:
    database_path: Path
    sessions_path: Path

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            database_path=Path(os.environ.get("LOCALLORE_DB", "/data/locallore.db")),
            sessions_path=Path(os.environ.get("LOCALLORE_SESSIONS", "/sessions")),
        )
