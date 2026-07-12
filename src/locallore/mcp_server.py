from __future__ import annotations

import logging

from mcp.server.fastmcp import FastMCP

from .config import Settings
from .status import Status, get_status

logging.basicConfig(level=logging.INFO)

mcp = FastMCP(
    "LocalLore",
    instructions="Offline memory for local Claude Code sessions.",
)


@mcp.tool()
def locallore_status() -> Status:
    """Report LocalLore index and offline-runtime status."""
    return get_status(Settings.from_env().database_path)


def run_server() -> None:
    """Serve MCP over stdio; stdout is reserved for protocol messages."""
    mcp.run(transport="stdio")
