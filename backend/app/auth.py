"""Shared-password protection for a hosted API.

With ``COMPCREATOR_PASSWORD`` set, every ``/api`` request must send it as
``Authorization: Bearer <password>``. A browser download link cannot send a
header, so the finished-video route also accepts a ``token`` signed for that
job id. That token unlocks only that one job's file. It is signed with a random
key made when the process starts, not with the password, so a leaked link
reveals nothing that helps guess the password, and every link stops working
when the server restarts, as its in-memory jobs do. A client that sends a wrong password or
token too often is refused with 429 for a while, so the password cannot be
guessed at network speed. Local and desktop servers usually set no password,
and then nothing is checked.
"""

from __future__ import annotations

import hashlib
import hmac
import math
import re
import secrets
from urllib.parse import parse_qs

from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Receive, Scope, Send

from app.config import settings
from app.errors import ConfigurationError
from app.throttle import FailureThrottle

_FILE_ROUTE = re.compile(r"/api/compilations/([0-9a-f]{32})/file")
# Signs download tokens. Jobs live only in this process, so their links may too.
_TOKEN_KEY = secrets.token_bytes(32)
# Short passwords fall to guessing even with the throttle below.
MIN_HOSTED_PASSWORD_LENGTH = 12
# Five wrong guesses per client every 15 minutes is under 500 a day.
_failures = FailureThrottle(limit=5, window=15 * 60)


def require_password_when_hosted() -> None:
    """Refuse to serve a hosted deploy that anyone could use without a password."""
    if settings.hosted and not settings.password:
        raise ConfigurationError(
            "Set COMPCREATOR_PASSWORD before starting a hosted server. "
            "Without it, anyone with the URL can run exports with this server's YouTube login."
        )
    too_short = len(settings.password or "") < MIN_HOSTED_PASSWORD_LENGTH
    if settings.hosted and too_short:
        raise ConfigurationError(
            f"COMPCREATOR_PASSWORD must be at least {MIN_HOSTED_PASSWORD_LENGTH} characters "
            "on a hosted server, so it cannot be guessed."
        )


def file_token(job_id: str) -> str:
    """The download token for ``job_id``'s file. Empty when no password is set."""
    if not settings.password:
        return ""
    return hmac.new(_TOKEN_KEY, f"file:{job_id}".encode(), hashlib.sha256).hexdigest()


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
        # Bytes, because compare_digest raises on non-ASCII str.
        return bool(supplied) and hmac.compare_digest(supplied.encode(), expected.encode())
    return False


def _sent_credentials(scope: Scope) -> bool:
    """Whether the request tried a password or token, as opposed to sending none."""
    if any(name == b"authorization" for name, _ in scope.get("headers", [])):
        return True
    query = parse_qs(scope.get("query_string", b"").decode("latin-1"))
    return bool(query.get("token"))


def _client_address(scope: Scope) -> str:
    """The caller's IP address, as seen by the hosting platform's proxy when hosted."""
    if settings.hosted:
        # Each trusted proxy appends the address it saw to whatever the caller
        # sent, so the entry that many places from the right is the caller.
        # Cloud Run's own URL is one hop; a load balancer or CDN in front adds
        # one each (COMPCREATOR_TRUSTED_PROXY_HOPS).
        for name, value in scope.get("headers", []):
            if name == b"x-forwarded-for":
                entries: list[str] = [item.strip() for item in value.decode("latin-1").split(",")]
                hops = settings.trusted_proxy_hops
                # Fewer entries than hops: the leftmost is the closest we have.
                chosen = entries[-hops] if len(entries) >= hops else entries[0]
                if chosen:
                    return chosen
    client = scope.get("client")
    return str(client[0]) if client else "unknown"


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
        """Pass the request on, or answer 401 or 429 when it may not use the API."""
        if (
            scope["type"] != "http"
            or not settings.password
            or not scope["path"].startswith("/api/")
            or scope["method"] == "OPTIONS"
        ):
            await self.app(scope, receive, send)
            return
        client = _client_address(scope)
        # Checked before the password, so a paused client learns nothing from guessing.
        wait = _failures.retry_after(client)
        if wait:
            minutes = math.ceil(wait / 60)
            response = JSONResponse(
                status_code=429,
                content={
                    "detail": "Too many wrong passwords. "
                    f"Try again in {minutes} minute{'s' if minutes != 1 else ''}."
                },
                headers={"Retry-After": str(wait)},
            )
            await response(scope, receive, send)
            return
        if _authorized(scope):
            _failures.clear(client)
            await self.app(scope, receive, send)
            return
        # A request without any password is how the UI asks whether one is
        # needed, so only a wrong guess counts against the client.
        if _sent_credentials(scope):
            _failures.record_failure(client)
        response = JSONResponse(
            status_code=401,
            content={"detail": "This server needs its password."},
            headers={"WWW-Authenticate": "Bearer"},
        )
        await response(scope, receive, send)
