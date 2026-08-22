from __future__ import annotations

import asyncio
import json
import re
import stat
import tomllib
from pathlib import Path

import yaml

from locallore import __version__
from locallore.server.mcp import locallore_status, mcp

ROOT = Path(__file__).parents[1]


def test_plugin_manifest_has_expected_identity_and_author() -> None:
    manifest = json.loads((ROOT / ".claude-plugin/plugin.json").read_text())
    project = tomllib.loads((ROOT / "pyproject.toml").read_text())

    assert manifest["name"] == "locallore"
    assert manifest["version"] == __version__
    assert manifest["version"] == project["project"]["version"]
    assert (
        (ROOT / "RELEASE_NOTES.md")
        .read_text()
        .startswith(f"# LocalLore {manifest['version']} Release Notes")
    )
    assert manifest["author"]["name"] == "Elar Saks"
    assert "userConfig" not in manifest


def test_repository_is_a_self_hosted_plugin_marketplace() -> None:
    manifest = json.loads((ROOT / ".claude-plugin/plugin.json").read_text())
    marketplace = json.loads((ROOT / ".claude-plugin/marketplace.json").read_text())
    plugin = marketplace["plugins"][0]

    assert marketplace["name"] == "locallore"
    assert plugin["name"] == manifest["name"]
    assert plugin["version"] == manifest["version"]
    assert plugin["source"] == "./"
    setup = (ROOT / "commands/setup.md").read_text()
    assert "${user_config" not in setup
    assert 'CLAUDE_PLUGIN_DATA="${CLAUDE_PLUGIN_DATA}"' in setup


def test_setup_reports_long_running_install_progress() -> None:
    setup = (ROOT / "commands/setup.md").read_text()
    installer = (ROOT / "scripts/install.sh").read_text()

    assert "Before invoking the installer, tell the user" in setup
    assert "Do not wait for the installer to finish" in setup
    for message in (
        "LocalLore image build complete.",
        "LocalLore daemon started. Waiting for initial session indexing...",
        "Still indexing Claude sessions (${elapsed}s elapsed)...",
        "Initial session indexing complete.",
        "Running LocalLore health and security checks...",
    ):
        assert message in installer


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
    assert service["healthcheck"]["test"][-1].endswith("timeout=2).read()")
    assert "noexec" in service["tmpfs"][0]


def test_launcher_scripts_are_executable_and_use_strict_mode() -> None:
    for name in (
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


def test_build_and_workflow_dependencies_are_immutable() -> None:
    full_sha = re.compile(r"[0-9a-f]{40}")
    for workflow in (ROOT / ".github/workflows").glob("*.yml"):
        for line in workflow.read_text().splitlines():
            match = re.search(r"uses:\s+(\S+)@(\S+)", line)
            if match is not None:
                assert full_sha.fullmatch(match.group(2)), line

    dockerfile = (ROOT / "Dockerfile").read_text()
    digest = r"sha256:[0-9a-f]{64}"
    assert re.search(rf"FROM python:[^\s@]+@{digest}", dockerfile)
    assert re.search(rf"COPY --from=ghcr\.io/astral-sh/uv:[^\s@]+@{digest}", dockerfile)
    assert re.search(r"revision='[0-9a-f]{40}'", dockerfile)

    project = tomllib.loads((ROOT / "pyproject.toml").read_text())
    requirements = [
        *project["project"]["dependencies"],
        *project["dependency-groups"]["dev"],
        *project["build-system"]["requires"],
    ]
    assert all("==" in requirement for requirement in requirements)


def test_mcp_configuration_uses_unauthenticated_loopback_http() -> None:
    manifest = json.loads((ROOT / ".claude-plugin/plugin.json").read_text())
    server = manifest["mcpServers"]["locallore"]

    assert server["type"] == "http"
    assert server["url"] == "http://127.0.0.1:8765/mcp"
    assert "headersHelper" not in server


def test_lifecycle_scripts_use_the_fixed_compose_project() -> None:
    library = (ROOT / "scripts/lib.sh").read_text()
    assert "docker compose -p locallore" in library
    assert "compose run" not in "\n".join(
        script.read_text() for script in (ROOT / "scripts").glob("*.sh")
    )
