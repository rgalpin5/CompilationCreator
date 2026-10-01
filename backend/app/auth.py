"""Shared-password protection for a hosted API.

With ``COMPCREATOR_PASSWORD`` set, every ``/api`` request must send it as
``Authorization: Bearer <password>``. A browser download link cannot send a
header, so the finished-video route also accepts a ``token`` derived from the
password and the job id. That token unlocks only that one job's file, and the
password itself never appears in a URL. Local and desktop servers usually set
no password, and then nothing is checked.
"""

from __future__ import annotations

import hashlib
import hmac
import re
from urllib.parse import parse_qs

from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Receive, Scope, Send

from app.config import settings
from app.errors import ConfigurationError

_FILE_ROUTE = re.compile(r"/api/compilations/([0-9a-f]{32})/file")


def require_password_when_hosted() -> None:
    """Refuse to serve a hosted deploy that anyone could use without a password."""
    if settings.hosted and not settings.password:
        raise ConfigurationError(
            "Set COMPCREATOR_PASSWORD before starting a hosted server. "
            "Without it, anyone with the URL can run exports with this server's YouTube login."
        )


def file_token(job_id: str) -> str:
    """The download token for ``job_id``'s file. Empty when no password is set."""
    if not settings.password:
        return ""
    key = settings.password.encode()
    return hmac.new(key, f"file:{job_id}".encode(), hashlib.sha256).hexdigest()


def _password_matches(supplied: str) -> bool:
    expected = settings.password or ""
    return hmac.compare_digest(supplied.encode(), expected.encode())


def _authorized(scope: Scope) -> bool:
    for name, value in scope.get("headers", []):
        if name == b"authorization":
            scheme, _, supplied = value.decode("latin-1").partition(" ")
            if scheme.lower() == "bearer" and _password_matches(supplied.strip()):
                return True
    match = _FILE_ROUTE.fullmatch(scope["path"])
    if match and scope["method"] in {"GET", "HEAD"}:
        query = parse_qs(scope.get("query_string", b"").decode("latin-1"))
        supplied = query.get("token", [""])[0]
        expected = file_token(match.group(1))
        return bool(supplied) and hmac.compare_digest(supplied, expected)
    return False


class PasswordMiddleware:
    """Reject ``/api`` requests without the shared password when one is set.

    Add it before ``CORSMiddleware`` so CORS stays outermost: preflights are
    answered without a password, and a 401 still carries CORS headers the
    browser can read.
    """

    def __init__(self, app: ASGIApp) -> None:
        """Wrap ``app``."""
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """Pass the request on, or answer 401 when the password is missing or wrong."""
        if (
            scope["type"] != "http"
            or not settings.password
            or not scope["path"].startswith("/api/")
            or scope["method"] == "OPTIONS"
            or _authorized(scope)
        ):
            await self.app(scope, receive, send)
            return
        response = JSONResponse(
            status_code=401,
            content={"detail": "This server needs its password."},
            headers={"WWW-Authenticate": "Bearer"},
        )
        await response(scope, receive, send)
