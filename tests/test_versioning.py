from __future__ import annotations

import shutil
import subprocess
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).parents[1]
SCRIPT = ROOT / "scripts" / "bump_version.py"
VERSION_FILES = (
    "pyproject.toml",
    "src/locallore/__init__.py",
    "src/locallore/config.py",
    "compose.yaml",
    "scripts/install.sh",
    ".claude-plugin/plugin.json",
    ".claude-plugin/marketplace.json",
    "RELEASE_NOTES.md",
)
CURRENT_VERSION = tomllib.loads((ROOT / "pyproject.toml").read_text())["project"][
    "version"
]
TARGET_VERSION = "99.99.99"


def run_version_command(
    *args: str, root: Path = ROOT
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args, "--root", str(root)],
        check=False,
        capture_output=True,
        text=True,
    )


def copy_version_files(destination: Path) -> None:
    for relative_path in VERSION_FILES:
        source = ROOT / relative_path
        target = destination / relative_path
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)


def test_committed_version_metadata_is_synchronized() -> None:
    result = run_version_command("--check")

    assert result.returncode == 0, result.stderr
    assert f"all version metadata matches {CURRENT_VERSION}" in result.stdout


def test_version_bump_updates_every_location(tmp_path: Path) -> None:
    copy_version_files(tmp_path)

    result = run_version_command(TARGET_VERSION, root=tmp_path)

    assert result.returncode == 0, result.stderr
    assert (
        f"updated 8 files from {CURRENT_VERSION} to {TARGET_VERSION}" in result.stdout
    )
    assert run_version_command("--check", root=tmp_path).returncode == 0
    for relative_path in VERSION_FILES:
        assert TARGET_VERSION in (tmp_path / relative_path).read_text()


def test_invalid_source_metadata_leaves_every_file_unchanged(tmp_path: Path) -> None:
    copy_version_files(tmp_path)
    installer = tmp_path / "scripts" / "install.sh"
    installer.write_text(
        installer.read_text().replace(
            f"VERSION={CURRENT_VERSION}",
            "VERSION=broken",
        )
    )
    before = {
        relative_path: (tmp_path / relative_path).read_bytes()
        for relative_path in VERSION_FILES
    }

    result = run_version_command(TARGET_VERSION, root=tmp_path)

    assert result.returncode != 0
    assert "scripts/install.sh" in result.stderr
    assert {
        relative_path: (tmp_path / relative_path).read_bytes()
        for relative_path in VERSION_FILES
    } == before
