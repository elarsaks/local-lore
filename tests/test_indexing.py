from __future__ import annotations

from pathlib import Path

from locallore.__main__ import index
from locallore.config import Settings
from locallore.embeddings import MODEL_CHECKSUM_FILE


def test_index_skips_model_initialization_when_embeddings_are_current(
    tmp_path: Path, monkeypatch,
) -> None:
    sessions = tmp_path / "sessions"
    models = tmp_path / "models"
    sessions.mkdir()
    models.mkdir()
    (models / MODEL_CHECKSUM_FILE).write_text(f"{'a' * 64}\n")
    settings = Settings(
        tmp_path / "locallore.db",
        sessions,
        models,
        "fixture",
        3,
        8,
    )

    def fail_model_initialization(*_args, **_kwargs):
        raise AssertionError("embedding model should remain lazy")

    monkeypatch.setattr(
        "locallore.__main__.FastEmbedder", fail_model_initialization
    )

    index(settings)
