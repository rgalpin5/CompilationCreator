"""Send one request through the whole FastAPI app, middleware included.

httpx is not a dependency, so the tests call the ASGI app directly instead of
using Starlette's TestClient. Tests that need the job and usage stores set them
on ``app.state`` the way the lifespan does.
"""

import asyncio

from starlette.types import Message

from app.main import app


def call(
    path: str,
    *,
    method: str = "GET",
    headers: dict[str, str] | None = None,
    query: str = "",
    body: bytes = b"",
    client: str = "127.0.0.1",
) -> tuple[int, dict[str, str], bytes]:
    """Return the status, the response headers (lowercase names) and the body."""
    scope = {
        "type": "http",
        "asgi": {"version": "3.0", "spec_version": "2.4"},
        "http_version": "1.1",
        "method": method,
        "scheme": "http",
        "path": path,
        "raw_path": path.encode(),
        "query_string": query.encode(),
        "headers": [(k.lower().encode(), v.encode()) for k, v in (headers or {}).items()],
        "client": (client, 50000),
        "server": ("127.0.0.1", 8000),
        "root_path": "",
        "app": app,
    }
    status = 0
    sent: dict[str, str] = {}
    received = bytearray()
    pending = [body]

    async def receive() -> Message:
        if pending:
            return {"type": "http.request", "body": pending.pop(), "more_body": False}
        return {"type": "http.disconnect"}

    async def send(message: Message) -> None:
        nonlocal status
        if message["type"] == "http.response.start":
            status = message["status"]
            sent.update({k.decode(): v.decode() for k, v in message["headers"]})
        elif message["type"] == "http.response.body":
            received.extend(message.get("body", b""))

    asyncio.run(app(scope, receive, send))
    return status, sent, bytes(received)
