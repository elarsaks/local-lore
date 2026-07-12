from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class SourceFile:
    path: Path
    relative_path: str
    identity: str
    size_bytes: int
    mtime_ns: int


def discover(root: Path) -> list[SourceFile]:
    root = root.resolve()
    sources: list[SourceFile] = []
    if not root.is_dir():
        raise FileNotFoundError(f"session directory does not exist: {root}")
    for path in sorted(root.rglob("*.jsonl")):
        try:
            resolved = path.resolve(strict=True)
            resolved.relative_to(root)
            if not resolved.is_file():
                continue
            stat = resolved.stat()
        except (FileNotFoundError, OSError, ValueError):
            continue
        sources.append(
            SourceFile(
                path=resolved,
                relative_path=resolved.relative_to(root).as_posix(),
                identity=f"{stat.st_dev}:{stat.st_ino}",
                size_bytes=stat.st_size,
                mtime_ns=stat.st_mtime_ns,
            )
        )
    return sources
