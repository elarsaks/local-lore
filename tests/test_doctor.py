from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from locallore.config import Settings
from locallore.doctor import DoctorError, run_doctor


class FakeEmbedder:
    def __init__(self, _name: str, _path: Path, dimension: int) -> None:
        self.dimension = dimension

    def encode_query(self, _query: str) -> np.ndarray:
        return np.ones(self.dimension, dtype=np.float32)


def settings(tmp_path: Path) -> Settings:
    sessions = tmp_path / "sessions"
    models = tmp_path / "models"
    sessions.mkdir()
    models.mkdir()
    (models / "model.onnx").write_bytes(b"fixture")
    return Settings(tmp_path / "data" / "db.sqlite", sessions, models, "fake", 3, 8)


def test_doctor_checks_runtime_prerequisites(tmp_path, monkeypatch) -> None:
    configured = settings(tmp_path)
    configured.database_path.parent.mkdir()
    monkeypatch.setenv("LOCALLORE_NETWORK_MODE", "none")
    monkeypatch.setattr("locallore.doctor.FastEmbedder", FakeEmbedder)

    report = run_doctor(configured)

    assert len(report.checks) == 5
    assert configured.database_path.exists()


def test_doctor_reports_missing_session_directory(tmp_path) -> None:
    configured = settings(tmp_path)
    configured.sessions_path.rmdir()

    with pytest.raises(DoctorError, match="session directory does not exist"):
        run_doctor(configured)


def test_doctor_requires_compose_offline_marker(tmp_path, monkeypatch) -> None:
    configured = settings(tmp_path)
    configured.database_path.parent.mkdir()
    monkeypatch.delenv("LOCALLORE_NETWORK_MODE", raising=False)
    monkeypatch.setattr("locallore.doctor.FastEmbedder", FakeEmbedder)

    with pytest.raises(DoctorError, match="cannot confirm the offline runtime"):
        run_doctor(configured)
