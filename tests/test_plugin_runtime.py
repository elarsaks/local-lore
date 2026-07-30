from __future__ import annotations

import asyncio
import json
import stat
from pathlib import Path

import yaml

from locallore.server.mcp import locallore_status, mcp


ROOT = Path(__file__).parents[1]


def test_plugin_manifest_has_expected_identity_and_author() -> None:
    manifest = json.loads((ROOT / ".claude-plugin/plugin.json").read_text())

    assert manifest["name"] == "locallore"
    assert manifest["version"] == "0.2.0"
    assert manifest["author"]["name"] == "Elar Saks"
    assert manifest["userConfig"]["port"]["default"] == 8765
    assert manifest["userConfig"]["projects_directory"]["type"] == "directory"


def test_mcp_exposes_the_status_tool() -> None:
    tools = asyncio.run(mcp.list_tools())

    assert [tool.name for tool in tools] == [
        "locallore_status",
        "locallore_search",
        "locallore_context",
    ]


def test_status_reports_an_empty_index_before_import() -> None:
    status = locallore_status()

    assert status["schema_version"] == 3
    assert status["sessions"] == 0
    assert status["messages"] == 0
    assert status["import_errors"] == []
    assert status["runtime_network"] == "not confirmed"
    assert status["transport"] == "streamable-http"
    assert status["refresh_state"] == "idle"


def test_compose_is_loopback_only_and_protects_sessions() -> None:
    compose = yaml.safe_load((ROOT / "compose.yaml").read_text())
    service = compose["services"]["locallore"]

    assert service["container_name"] == "locallore"
    assert service["restart"] == "unless-stopped"
    assert service["command"] == ["serve"]
    assert service["ports"] == ["127.0.0.1:${LOCALLORE_PORT:-8765}:8000"]
    assert compose["networks"]["locallore-local"]["driver"] == "bridge"
    assert "internal" not in compose["networks"]["locallore-local"]
    assert service["networks"] == ["locallore-local"]
    assert service["read_only"] is True
    assert "ALL" in service["cap_drop"]
    assert service["user"] == "65532:65532"
    assert service["init"] is True
    assert service["pids_limit"] == 128
    assert "no-new-privileges:true" in service["security_opt"]
    sessions_mount = next(
        mount for mount in service["volumes"] if mount["target"] == "/sessions"
    )
    assert sessions_mount["read_only"] is True
    assert service["environment"]["LOCALLORE_MODEL_PATH"] == "/models"
    assert service["environment"]["LOCALLORE_EMBEDDING_DIMENSION"] == "384"
    assert "outbound access enabled" in service["environment"]["LOCALLORE_NETWORK_MODE"]
    assert service["environment"]["LOCALLORE_TRANSPORT"] == "streamable-http"
    assert "LOCALLORE_TOKEN" in service["environment"]
    assert service["healthcheck"]["test"][-1].endswith("timeout=2).read()")
    assert "noexec" in service["tmpfs"][0]


def test_launcher_scripts_are_executable_and_use_strict_mode() -> None:
    for name in (
        "mcp-headers.sh",
        "install.sh",
        "doctor.sh",
        "status.sh",
        "logs.sh",
        "uninstall.sh",
    ):
        script = ROOT / "scripts" / name
        mode = script.stat().st_mode
        assert mode & (stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
        content = script.read_text()
        assert "set -eu" in content


def test_mcp_configuration_uses_http_and_dynamic_headers() -> None:
    manifest = json.loads((ROOT / ".claude-plugin/plugin.json").read_text())
    server = manifest["mcpServers"]["locallore"]

    assert server["type"] == "http"
    assert server["url"] == "http://127.0.0.1:${user_config.port}/mcp"
    assert server["headersHelper"] == ('"${CLAUDE_PLUGIN_ROOT}/scripts/mcp-headers.sh"')


def test_lifecycle_scripts_use_the_fixed_compose_project() -> None:
    library = (ROOT / "scripts/lib.sh").read_text()
    assert "docker compose -p locallore" in library
    assert "--no-build" in (ROOT / "scripts/mcp-headers.sh").read_text()
    assert "compose run" not in "\n".join(
        script.read_text() for script in (ROOT / "scripts").glob("*.sh")
    )
