from __future__ import annotations

import hmac

from mcp.server.auth.provider import AccessToken
from starlette.requests import Request

from ..config import Settings


def token_matches(token: str, expected: str) -> bool:
    """Compare a token with the configured secret in constant time."""
    return bool(expected and hmac.compare_digest(token, expected))


def bearer_token_matches(value: str, expected: str) -> bool:
    """Validate one Authorization header value in constant time."""
    prefix = "Bearer "
    return value.startswith(prefix) and token_matches(value[len(prefix) :], expected)


def is_authorized(request: Request) -> bool:
    """Validate a request using the configured installation-scoped token."""
    return bearer_token_matches(
        request.headers.get("authorization", ""),
        Settings.from_env().bearer_token,
    )


class LocalBearerTokenVerifier:
    """Adapt the installation-scoped token to the MCP auth interface."""

    async def verify_token(self, token: str) -> AccessToken | None:
        expected = Settings.from_env().bearer_token
        if not token_matches(token, expected):
            return None
        return AccessToken(
            token=token,
            client_id="locallore-local-client",
            scopes=[],
        )
