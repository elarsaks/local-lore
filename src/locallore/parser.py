from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from .models import ParsedMessage


def _text(content: Any) -> str:
    if isinstance(content, str):
        return content
    if not isinstance(content, list):
        return ""
    parts: list[str] = []
    for block in content:
        if not isinstance(block, dict):
            continue
        if block.get("type") == "text" and isinstance(block.get("text"), str):
            parts.append(block["text"])
        elif block.get("type") == "tool_use":
            parts.append(f"Tool use: {block.get('name', 'unknown')}")
        elif block.get("type") == "tool_result":
            result = block.get("content")
            if isinstance(result, str):
                parts.append(result)
    return "\n".join(parts)


def parse_record(payload: object, source: Path, line: int) -> ParsedMessage | None:
    if not isinstance(payload, dict):
        return None
    message = payload.get("message")
    if not isinstance(message, dict):
        return None
    role = message.get("role")
    if role not in {"user", "assistant", "tool"}:
        return None
    session_id = payload.get("sessionId") or payload.get("session_id")
    if not isinstance(session_id, str) or not session_id:
        session_id = source.stem
    text = _text(message.get("content"))
    if not text:
        return None
    raw_id = message.get("id") or payload.get("uuid")
    if not isinstance(raw_id, str) or not raw_id:
        raw_id = hashlib.sha256(f"{source}:{line}:{text}".encode()).hexdigest()
    cwd = payload.get("cwd")
    project = payload.get("project") or payload.get("projectName")
    return ParsedMessage(
        session_id=session_id,
        message_id=raw_id,
        role=role,
        raw_type=str(payload.get("type", role)),
        timestamp=payload.get("timestamp") if isinstance(payload.get("timestamp"), str) else None,
        text=text,
        cwd=cwd if isinstance(cwd, str) else None,
        project=project if isinstance(project, str) else None,
    )


def decode_line(raw: bytes) -> object:
    return json.loads(raw.decode("utf-8"))
