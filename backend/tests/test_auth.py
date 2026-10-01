import asyncio
import json
import unittest
import uuid
from unittest.mock import patch

from starlette.types import Message

from app.auth import file_token, require_password_when_hosted
from app.config import settings
from app.errors import ConfigurationError
from app.main import app

_SECRET = "correct horse battery staple"


def _call(
    path: str,
    *,
    method: str = "GET",
    headers: dict[str, str] | None = None,
    query: str = "",
) -> tuple[int, dict[str, str], bytes]:
    """Send one request through the full app, middleware included."""
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
        "client": ("127.0.0.1", 50000),
        "server": ("127.0.0.1", 8000),
        "root_path": "",
        "app": app,
    }
    status = 0
    sent: dict[str, str] = {}
    body = bytearray()

    async def receive() -> Message:
        return {"type": "http.request", "body": b"", "more_body": False}

    async def send(message: Message) -> None:
        nonlocal status
        if message["type"] == "http.response.start":
            status = message["status"]
            sent.update({k.decode(): v.decode() for k, v in message["headers"]})
        elif message["type"] == "http.response.body":
            body.extend(message.get("body", b""))

    asyncio.run(app(scope, receive, send))
    return status, sent, bytes(body)


class PasswordTests(unittest.TestCase):
    def test_no_password_leaves_the_api_open(self) -> None:
        with patch.object(settings, "password", None):
            status, _, _ = _call("/api/session")
        self.assertEqual(status, 200)

    def test_password_is_required_for_the_api_but_not_health(self) -> None:
        with patch.object(settings, "password", _SECRET):
            missing, headers, body = _call("/api/session")
            wrong, _, _ = _call("/api/session", headers={"Authorization": "Bearer nope"})
            right, _, _ = _call("/api/session", headers={"Authorization": f"Bearer {_SECRET}"})
            health, _, _ = _call("/health")
        self.assertEqual(missing, 401)
        self.assertEqual(headers["www-authenticate"], "Bearer")
        self.assertEqual(json.loads(body)["detail"], "This server needs its password.")
        self.assertEqual(wrong, 401)
        self.assertEqual(right, 200)
        self.assertEqual(health, 200)

    def test_a_401_still_carries_cors_headers_and_preflight_needs_no_password(self) -> None:
        origin = settings.cors_origins[0]
        with patch.object(settings, "password", _SECRET):
            status, headers, _ = _call("/api/session", headers={"Origin": origin})
            preflight, pre_headers, _ = _call(
                "/api/session",
                method="OPTIONS",
                headers={
                    "Origin": origin,
                    "Access-Control-Request-Method": "GET",
                    "Access-Control-Request-Headers": "authorization",
                },
            )
        self.assertEqual(status, 401)
        self.assertEqual(headers["access-control-allow-origin"], origin)
        self.assertEqual(preflight, 200)
        self.assertEqual(pre_headers["access-control-allow-origin"], origin)

    def test_file_token_unlocks_only_its_own_job_file(self) -> None:
        job_id = uuid.uuid4().hex
        other_id = uuid.uuid4().hex
        with patch.object(settings, "password", _SECRET):
            token = file_token(job_id)
            # 500 means the request got past the password check to the route,
            # which has no job store in this bare app.
            own, _, _ = _call(f"/api/compilations/{job_id}/file", query=f"token={token}")
            other, _, _ = _call(f"/api/compilations/{other_id}/file", query=f"token={token}")
            status_page, _, _ = _call(f"/api/compilations/{job_id}", query=f"token={token}")
        self.assertNotIn(_SECRET, token)
        self.assertNotEqual(own, 401)
        self.assertEqual(other, 401)
        self.assertEqual(status_page, 401)

    def test_no_password_means_no_token(self) -> None:
        with patch.object(settings, "password", None):
            self.assertEqual(file_token(uuid.uuid4().hex), "")

    def test_hosted_server_without_a_password_refuses_to_start(self) -> None:
        with (
            patch.object(settings, "hosted", True),
            patch.object(settings, "password", None),
            self.assertRaisesRegex(ConfigurationError, "COMPCREATOR_PASSWORD"),
        ):
            require_password_when_hosted()
        with patch.object(settings, "hosted", True), patch.object(settings, "password", _SECRET):
            require_password_when_hosted()
        with patch.object(settings, "hosted", False), patch.object(settings, "password", None):
            require_password_when_hosted()


if __name__ == "__main__":
    unittest.main()
