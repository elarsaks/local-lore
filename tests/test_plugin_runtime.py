from __future__ import annotations

import asyncio
import json
import stat
from pathlib import Path

import yaml

from locallore.__main__ import embedding_progress
from locallore.mcp_server import locallore_status, mcp


ROOT = Path(__file__).parents[1]


def test_plugin_manifest_has_expected_identity_and_author() -> None:
    manifest = json.loads((ROOT / ".claude-plugin/plugin.json").read_text())

    assert manifest["name"] == "locallore"
    assert manifest["version"] == "0.1.0"
    assert manifest["author"]["name"] == "Elar Saks"


def test_mcp_exposes_the_status_tool() -> None:
    tools = asyncio.run(mcp.list_tools())

    assert [tool.name for tool in tools] == [
        "locallore_status",
        "locallore_configure",
        "locallore_search",
        "locallore_context",
    ]


def test_mcp_instructions_require_first_run_offer_for_an_empty_index() -> None:
    instructions = mcp.instructions

    assert instructions is not None
    assert "start of every Claude Code session" in instructions
    assert "call locallore_status" in instructions
    assert "messages value is 0" in instructions
    assert "ask the user whether they want to set up LocalLore" in instructions
    assert "Do not start setup without confirmation" in instructions
    assert "Do not make this offer when messages is greater than 0" in instructions


def test_status_reports_an_empty_index_before_import() -> None:
    status = locallore_status()

    assert status["schema_version"] == 4
    assert status["sessions"] == 0
    assert status["messages"] == 0
    assert status["import_errors"] == []
    assert status["runtime_network"] == "disabled by Docker Compose"
    assert status["configured"] is False
    assert status["history_after"] is None


def test_compose_disables_network_and_protects_sessions() -> None:
    compose = yaml.safe_load((ROOT / "compose.yaml").read_text())
    service = compose["services"]["locallore"]

    assert service["network_mode"] == "none"
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
    assert service["environment"]["LOCALLORE_NETWORK_MODE"] == "none"
    assert "noexec" in service["tmpfs"][0]


def test_launcher_scripts_are_executable_and_use_strict_mode() -> None:
    for name in (
        "mcp.sh",
        "build.sh",
        "index.sh",
        "doctor.sh",
        "configure.sh",
        "setup.sh",
        "onboarding.sh",
    ):
        script = ROOT / "scripts" / name
        mode = script.stat().st_mode
        assert mode & (stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
        content = script.read_text()
        assert "set -eu" in content


def test_compose_launchers_use_a_stable_marketplace_project_name() -> None:
    for name in ("mcp.sh", "build.sh", "index.sh", "doctor.sh", "configure.sh"):
        content = (ROOT / "scripts" / name).read_text()
        assert "--project-name locallore" in content


def test_first_prompt_hook_offers_first_run_onboarding() -> None:
    hooks = json.loads((ROOT / "hooks/hooks.json").read_text())
    assert "SessionStart" not in hooks["hooks"]
    handler = hooks["hooks"]["UserPromptSubmit"][0]["hooks"][0]

    assert handler["command"] == "${CLAUDE_PLUGIN_ROOT}/scripts/onboarding.sh"
    assert handler["args"] == ["${CLAUDE_PLUGIN_DATA}"]
    onboarding = (ROOT / "scripts/onboarding.sh").read_text()
    assert "setup-complete" in onboarding
    assert "onboarding-offered" not in onboarding


def test_setup_command_runs_the_marketplace_safe_bootstrap() -> None:
    content = (ROOT / "commands/setup.md").read_text()

    assert "${CLAUDE_PLUGIN_ROOT}/scripts/setup.sh" in content
    assert "${CLAUDE_PLUGIN_DATA}" in content
    assert "Only after explicit confirmation" in content


def test_setup_and_embedding_progress_are_visible_and_determinate() -> None:
    setup = (ROOT / "scripts/setup.sh").read_text()

    assert 'progress 1 "Building the offline runtime' in setup
    assert 'progress 5 "Ready"' in setup
    assert "today|1_week|1_month|3_months|1_year|all" in setup
    assert embedding_progress(25, 100, width=8) == (
        "Embedding messages [##------] 25/100 (25%)"
    )
    assert embedding_progress(0, 0, width=4) == (
        "Embedding messages [####] 0/0 (100%)"
    )


def test_mcp_configuration_uses_the_plugin_root_launcher() -> None:
    config = json.loads((ROOT / ".mcp.json").read_text())

    assert config["mcpServers"]["locallore"]["command"] == (
        "${CLAUDE_PLUGIN_ROOT}/scripts/mcp.sh"
    )
