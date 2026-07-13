from __future__ import annotations

import logging
from functools import lru_cache

from mcp.server.fastmcp import FastMCP

from .config import Settings
from .db import connect, migrate
from .embeddings import FastEmbedder
from .search import get_context, search_messages
from .status import Status, get_status
from .preferences import configure_history, get_history_setting

logging.basicConfig(level=logging.INFO)

mcp = FastMCP(
    "LocalLore",
    instructions=(
        "LocalLore is offline memory for local Claude Code sessions. At the "
        "start of every Claude Code session, call locallore_status before "
        "answering the user's first prompt. If configured is false, ask "
        "the user whether they want to set up LocalLore. Do not start setup "
        "without confirmation. If they agree, ask which history window to "
        "index (today, one week, one month (recommended), three months, one "
        "year, or all available history), then use the locallore setup "
        "command. Do not make this offer when configured is true."
    ),
)


@lru_cache(maxsize=1)
def _embedder() -> FastEmbedder:
    settings = Settings.from_env()
    return FastEmbedder(
        settings.embedding_model,
        settings.model_path,
        settings.embedding_dimension,
    )


@mcp.tool()
def locallore_status() -> Status:
    """Report index status. Call this at session start to detect an empty index."""
    return get_status(Settings.from_env().database_path)


@mcp.tool()
def locallore_configure(history: str) -> dict[str, object]:
    """Set the first-run history window before indexing session memory."""
    settings = Settings.from_env()
    with connect(settings.database_path) as connection:
        migrate(connection)
        cutoff = configure_history(connection, history)
    return {
        "configured": True,
        "history": history,
        "history_after": None if cutoff == "all" else cutoff,
        "next_step": (
            "Indexing is CPU-intensive and can take several minutes. Run "
            "scripts/index.sh, then reconnect LocalLore from /mcp."
        ),
    }


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
        if get_history_setting(connection) is None:
            raise ValueError(
                "LocalLore is not configured. Run /locallore:setup and choose "
                "a history window before searching."
            )
        return search_messages(
            connection,
            query,
            embedder=_embedder(),
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
