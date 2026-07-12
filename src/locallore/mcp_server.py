from __future__ import annotations

import logging

from mcp.server.fastmcp import FastMCP

from .config import Settings
from .db import connect
from .search import get_context, search_messages
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


@mcp.tool()
def locallore_search(
    query: str,
    project: str | None = None,
    after: str | None = None,
    before: str | None = None,
    role: str | None = None,
    files: list[str] | None = None,
    limit: int = 8,
) -> dict[str, object]:
    """Search indexed session history using full-text search and filters."""
    with connect(Settings.from_env().database_path) as connection:
        return search_messages(
            connection,
            query,
            project=project,
            after=after,
            before=before,
            role=role,
            files=files,
            limit=limit,
        )


@mcp.tool()
def locallore_context(
    session_id: str,
    message_id: str,
    before: int = 3,
    after: int = 3,
) -> dict[str, object]:
    """Return bounded messages surrounding one search result."""
    with connect(Settings.from_env().database_path) as connection:
        return get_context(
            connection, session_id, message_id, before=before, after=after
        )


def run_server() -> None:
    """Serve MCP over stdio; stdout is reserved for protocol messages."""
    mcp.run(transport="stdio")
