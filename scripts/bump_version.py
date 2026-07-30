#!/usr/bin/env python3
"""Synchronize LocalLore's committed release version."""

from __future__ import annotations

import argparse
import re
import tomllib
from dataclasses import dataclass
from pathlib import Path

VERSION_PATTERN = re.compile(r"^\d+\.\d+\.\d+$")


class VersionError(RuntimeError):
    """Raised when committed version metadata is inconsistent."""


@dataclass(frozen=True, slots=True)
class VersionLocation:
    path: str
    token: str
    expected: int


VERSION_LOCATIONS = (
    VersionLocation("pyproject.toml", 'version = "{version}"', 1),
    VersionLocation("src/locallore/__init__.py", '__version__ = "{version}"', 1),
    VersionLocation("src/locallore/config.py", '"{version}"', 2),
    VersionLocation("compose.yaml", "{version}", 2),
    VersionLocation("scripts/install.sh", "VERSION={version}", 1),
    VersionLocation(".claude-plugin/plugin.json", '"version": "{version}"', 1),
    VersionLocation(".claude-plugin/marketplace.json", '"version": "{version}"', 1),
    VersionLocation("RELEASE_NOTES.md", "{version}", 3),
)


def current_version(root: Path) -> str:
    project = tomllib.loads((root / "pyproject.toml").read_text())
    version = project["project"]["version"]
    if not isinstance(version, str) or VERSION_PATTERN.fullmatch(version) is None:
        raise VersionError(f"invalid project version: {version!r}")
    return version


def plan_updates(root: Path, current: str, target: str) -> dict[Path, str]:
    errors: list[str] = []
    updates: dict[Path, str] = {}
    for location in VERSION_LOCATIONS:
        path = root / location.path
        if not path.is_file():
            errors.append(f"missing version file: {location.path}")
            continue
        text = path.read_text()
        current_token = location.token.format(version=current)
        occurrences = text.count(current_token)
        if occurrences != location.expected:
            errors.append(
                f"{location.path}: expected {location.expected} occurrence(s) of "
                f"{current_token!r}, found {occurrences}"
            )
            continue
        target_token = location.token.format(version=target)
        updates[path] = text.replace(current_token, target_token)
    if errors:
        raise VersionError("\n".join(errors))
    return updates


def apply_updates(updates: dict[Path, str]) -> None:
    for path, content in updates.items():
        path.write_text(content)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Synchronize all committed LocalLore version metadata."
    )
    parser.add_argument("version", nargs="?", help="new X.Y.Z release version")
    parser.add_argument(
        "--check",
        action="store_true",
        help="verify version metadata without changing files",
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=Path(__file__).resolve().parents[1],
        help=argparse.SUPPRESS,
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    root = args.root.resolve()
    current = current_version(root)
    if args.check:
        if args.version is not None:
            raise VersionError("--check does not accept a target version")
        plan_updates(root, current, current)
        print(f"ok: all version metadata matches {current}")
        return
    if args.version is None:
        raise VersionError("a target X.Y.Z version is required")
    if VERSION_PATTERN.fullmatch(args.version) is None:
        raise VersionError(f"invalid release version: {args.version!r}")
    if args.version == current:
        raise VersionError(f"release version is already {current}")
    updates = plan_updates(root, current, args.version)
    apply_updates(updates)
    print(f"updated {len(updates)} files from {current} to {args.version}")


if __name__ == "__main__":
    try:
        main()
    except VersionError as exc:
        raise SystemExit(f"error: {exc}") from exc
