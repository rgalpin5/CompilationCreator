"""Refuse requests addressed to another host name on an open local server.

A local or desktop server with no password trusts anything that can reach it.
A web page can point its own domain at 127.0.0.1 (DNS rebinding) and then call
the API as a same-origin page. The browser still sends that domain in the Host
header, so accepting only loopback names stops it. A hosted server, or any
server with a password, is protected by the password instead.
"""

from __future__ import annotations

from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Receive, Scope, Send

from app.config import settings

_LOOPBACK_NAMES = frozenset({"localhost", "127.0.0.1", "::1"})


def host_name(header: str) -> str:
    """The name in a Host header, without its port or IPv6 brackets."""
    value = header.strip().lower()
    if value.startswith("["):
        return value[1:].split("]", 1)[0]
    return value.rsplit(":", 1)[0] if value.count(":") == 1 else value


class LocalHostMiddleware:
    """Answer 400 to a request for a non-loopback host on an open local server."""

    def __init__(self, app: ASGIApp) -> None:
        """Wrap ``app``."""
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """Pass the request on unless it names a host this server does not answer to."""
        if scope["type"] == "http" and not settings.hosted and not settings.password:
            host = next((v for k, v in scope.get("headers", []) if k == b"host"), None)
            # Browsers always send Host, so a request without one is not a
            # rebinding attack and is let through.
            if host is not None and host_name(host.decode("latin-1")) not in _LOOPBACK_NAMES:
                response = JSONResponse(
                    status_code=400,
                    content={
                        "detail": "This server only answers on localhost. "
                        "Set COMPCREATOR_PASSWORD to reach it from another address."
                    },
                )
                await response(scope, receive, send)
                return
        await self.app(scope, receive, send)
