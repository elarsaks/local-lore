from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from mcp.server.auth.settings import AuthSettings
from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings
from pydantic import AnyHttpUrl
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse

from ..config import Settings
from ..search import ContextResponse, SearchResponse, get_context, search_messages
from ..status import Status, get_status
from ..storage.db import connect
from .auth import LocalBearerTokenVerifier, is_authorized
from .runtime import LocalLoreRuntime

logger = logging.getLogger(__name__)

_runtime: LocalLoreRuntime | None = None


@asynccontextmanager
async def _daemon_lifespan(app: Starlette) -> AsyncIterator[None]:
    global _runtime
    runtime = LocalLoreRuntime(Settings.from_env())
    await runtime.start()
    _runtime = runtime
    original_lifespan = app.state.locallore_original_lifespan
    try:
        async with original_lifespan(app):
            yield
    finally:
        _runtime = None
        await runtime.stop()


def _transport_security(settings: Settings) -> TransportSecuritySettings:
    port = settings.public_port
    return TransportSecuritySettings(
        enable_dns_rebinding_protection=True,
        allowed_hosts=[
            f"127.0.0.1:{port}",
            f"localhost:{port}",
            f"[::1]:{port}",
        ],
        allowed_origins=[
            f"http://127.0.0.1:{port}",
            f"http://localhost:{port}",
            f"http://[::1]:{port}",
        ],
    )


_initial_settings = Settings.from_env()
mcp = FastMCP(
    "LocalLore",
    instructions="Offline memory for local Claude Code sessions.",
    host=_initial_settings.http_host,
    port=_initial_settings.http_port,
    streamable_http_path="/mcp",
    stateless_http=True,
    json_response=True,
    token_verifier=LocalBearerTokenVerifier(),
    auth=AuthSettings(
        issuer_url=AnyHttpUrl(f"http://127.0.0.1:{_initial_settings.public_port}/"),
        resource_server_url=None,
    ),
    transport_security=_transport_security(_initial_settings),
)


@mcp.custom_route(  # type: ignore[untyped-decorator]
    "/healthz", methods=["GET"], include_in_schema=False
)
async def healthz(_request: Request) -> JSONResponse:
    """Return non-sensitive liveness after migration and listener startup."""
    return JSONResponse({"status": "ok"})


@mcp.custom_route(  # type: ignore[untyped-decorator]
    "/statusz", methods=["GET"], include_in_schema=False
)
async def statusz(request: Request) -> JSONResponse:
    if not is_authorized(request):
        return JSONResponse({"error": "unauthorized"}, status_code=401)
    runtime = _runtime
    status = get_status(
        Settings.from_env().database_path,
        runtime.status() if runtime is not None else None,
    )
    return JSONResponse(status)


@mcp.custom_route(  # type: ignore[untyped-decorator]
    "/admin/refresh", methods=["POST"], include_in_schema=False
)
async def request_refresh(request: Request) -> JSONResponse:
    if not is_authorized(request):
        return JSONResponse({"error": "unauthorized"}, status_code=401)
    if _runtime is None:
        return JSONResponse({"error": "runtime is not ready"}, status_code=503)
    _runtime.request_refresh()
    return JSONResponse({"queued": True}, status_code=202)


@mcp.tool()
def locallore_status() -> Status:
    """Report LocalLore index and offline-runtime status."""
    runtime = _runtime
    return get_status(
        Settings.from_env().database_path,
        runtime.status() if runtime is not None else None,
    )


@mcp.tool()
def locallore_search(
    query: str,
    project: str | None = None,
    after: str | None = None,
    before: str | None = None,
    role: str | None = None,
    files: list[str] | None = None,
    limit: int = 8,
) -> SearchResponse:
    """Search indexed session history using full-text search and filters."""
    runtime = _runtime
    if runtime is None:
        raise RuntimeError("LocalLore HTTP runtime is not ready")
    with connect(Settings.from_env().database_path) as connection:
        return search_messages(
            connection,
            query,
            embedder=runtime.search_embedder,
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
) -> ContextResponse:
    """Return bounded messages surrounding one search result."""
    with connect(Settings.from_env().database_path) as connection:
        return get_context(
            connection, session_id, message_id, before=before, after=after
        )


def run_http_server(settings: Settings) -> None:
    """Serve the persistent, multi-client Streamable HTTP transport."""
    if len(settings.bearer_token) < 32:
        raise ValueError(
            "LOCALLORE_TOKEN is missing or too short; run ./scripts/install.sh"
        )
    import uvicorn

    app = mcp.streamable_http_app()
    app.state.locallore_original_lifespan = app.router.lifespan_context
    app.router.lifespan_context = _daemon_lifespan
    uvicorn.run(
        app,
        host=settings.http_host,
        port=settings.http_port,
        log_level="info",
    )
