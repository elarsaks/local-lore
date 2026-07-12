from __future__ import annotations

from typing import TypedDict


class Status(TypedDict):
    schema_version: int
    last_refresh: None
    sessions: int
    messages: int
    embedded_messages: int
    embedding_model_id: None
    import_errors: list[str]
    runtime_network: str


def get_status() -> Status:
    """Return the empty-but-healthy Milestone 1 index status."""
    return {
        "schema_version": 0,
        "last_refresh": None,
        "sessions": 0,
        "messages": 0,
        "embedded_messages": 0,
        "embedding_model_id": None,
        "import_errors": [],
        "runtime_network": "disabled by Docker Compose",
    }
