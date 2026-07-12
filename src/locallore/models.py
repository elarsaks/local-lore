from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ParsedMessage:
    session_id: str
    message_id: str
    role: str
    raw_type: str
    timestamp: str | None
    text: str
    cwd: str | None
    project: str | None
    file_operations: tuple[tuple[str, str], ...] = ()
