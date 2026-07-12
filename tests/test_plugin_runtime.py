from __future__ import annotations

import asyncio
import json
import stat
from pathlib import Path

import yaml

from locallore.mcp_server import locallore_status, mcp


ROOT = Path(__file__).parents[1]


def test_plugin_manifest_has_expected_identity_and_author() -> None:
    manifest = json.loads((ROOT / ".claude-plugin/plugin.json").read_text())

    assert manifest["name"] == "locallore"
    assert manifest["version"] == "0.1.0"
    assert manifest["author"]["name"] == "Elar Saks"


def test_mcp_exposes_the_status_tool() -> None:
    tools = asyncio.run(mcp.list_tools())

    assert [tool.name for tool in tools] == ["locallore_status"]


def test_status_reports_an_empty_index_before_import() -> None:
    status = locallore_status()

    assert status["schema_version"] == 1
    assert status["sessions"] == 0
    assert status["messages"] == 0
    assert status["import_errors"] == []
    assert status["runtime_network"] == "disabled by Docker Compose"


def test_compose_disables_network_and_protects_sessions() -> None:
    compose = yaml.safe_load((ROOT / "compose.yaml").read_text())
    service = compose["services"]["locallore"]

    assert service["network_mode"] == "none"
    assert service["read_only"] is True
    assert "ALL" in service["cap_drop"]
    sessions_mount = next(
        mount for mount in service["volumes"] if mount["target"] == "/sessions"
    )
    assert sessions_mount["read_only"] is True


def test_launcher_scripts_are_executable_and_use_strict_mode() -> None:
    for name in ("mcp.sh", "build.sh", "index.sh", "doctor.sh"):
        script = ROOT / "scripts" / name
        mode = script.stat().st_mode
        assert mode & (stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
        content = script.read_text()
        assert "set -eu" in content


def test_mcp_configuration_uses_the_plugin_root_launcher() -> None:
    config = json.loads((ROOT / ".mcp.json").read_text())

    assert config["mcpServers"]["locallore"]["command"] == (
        "${CLAUDE_PLUGIN_ROOT}/scripts/mcp.sh"
    )
