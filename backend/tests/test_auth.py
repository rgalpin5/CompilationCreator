import hashlib
import hmac
import json
import unittest
import uuid
from unittest.mock import patch

from app import auth
from app.auth import file_token, require_password_when_hosted
from app.config import settings
from app.errors import ConfigurationError
from app.throttle import FailureThrottle
from tests.asgi import call

_SECRET = "correct horse battery staple"


class PasswordTests(unittest.TestCase):
    def setUp(self) -> None:
        throttle = patch.object(auth, "_failures", FailureThrottle(limit=5, window=900))
        throttle.start()
        self.addCleanup(throttle.stop)

    def test_no_password_leaves_the_api_open(self) -> None:
        with patch.object(settings, "password", None):
            status, _, _ = call("/api/session")
        self.assertEqual(status, 200)

    def test_password_is_required_for_the_api_but_not_health(self) -> None:
        with patch.object(settings, "password", _SECRET):
            missing, headers, body = call("/api/session")
            wrong, _, _ = call("/api/session", headers={"Authorization": "Bearer nope"})
            right, _, _ = call("/api/session", headers={"Authorization": f"Bearer {_SECRET}"})
            health, _, _ = call("/health")
        self.assertEqual(missing, 401)
        self.assertEqual(headers["www-authenticate"], "Bearer")
        self.assertEqual(json.loads(body)["detail"], "This server needs its password.")
        self.assertEqual(wrong, 401)
        self.assertEqual(right, 200)
        self.assertEqual(health, 200)

    def test_a_401_still_carries_cors_headers_and_preflight_needs_no_password(self) -> None:
        origin = settings.cors_origins[0]
        with patch.object(settings, "password", _SECRET):
            status, headers, _ = call("/api/session", headers={"Origin": origin})
            preflight, pre_headers, _ = call(
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
        self.assertNotIn("access-control-allow-credentials", pre_headers)

    def test_preflight_refuses_methods_and_headers_the_api_does_not_use(self) -> None:
        origin = settings.cors_origins[0]
        bad_method, _, _ = call(
            "/api/session",
            method="OPTIONS",
            headers={"Origin": origin, "Access-Control-Request-Method": "DELETE"},
        )
        bad_header, _, _ = call(
            "/api/session",
            method="OPTIONS",
            headers={
                "Origin": origin,
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "x-custom",
            },
        )
        self.assertEqual(bad_method, 400)
        self.assertEqual(bad_header, 400)

    def test_file_token_unlocks_only_its_own_job_file(self) -> None:
        job_id = uuid.uuid4().hex
        other_id = uuid.uuid4().hex
        with patch.object(settings, "password", _SECRET):
            token = file_token(job_id)
            # 500 means the request got past the password check to the route,
            # which has no job store in this bare app.
            own, _, _ = call(f"/api/compilations/{job_id}/file", query=f"token={token}")
            other, _, _ = call(f"/api/compilations/{other_id}/file", query=f"token={token}")
            status_page, _, _ = call(f"/api/compilations/{job_id}", query=f"token={token}")
        self.assertNotIn(_SECRET, token)
        self.assertNotEqual(own, 401)
        self.assertEqual(other, 401)
        self.assertEqual(status_page, 401)

    def test_repeated_wrong_passwords_pause_that_client(self) -> None:
        wrong = {"Authorization": "Bearer nope"}
        right = {"Authorization": f"Bearer {_SECRET}"}
        with patch.object(settings, "password", _SECRET):
            first_five = [call("/api/session", headers=wrong)[0] for _ in range(5)]
            paused, headers, body = call("/api/session", headers=right)
            other_client, _, _ = call("/api/session", headers=right, client="10.0.0.9")
        self.assertEqual(first_five, [401] * 5)
        self.assertEqual(paused, 429)
        self.assertGreater(int(headers["retry-after"]), 0)
        self.assertIn("Too many wrong passwords", json.loads(body)["detail"])
        self.assertEqual(other_client, 200)

    def test_wrong_file_tokens_count_but_requests_without_a_password_do_not(self) -> None:
        job_id = uuid.uuid4().hex
        with patch.object(settings, "password", _SECRET):
            for _ in range(10):
                call("/api/session")
            still_allowed, _, _ = call(
                "/api/session", headers={"Authorization": f"Bearer {_SECRET}"}
            )
            for _ in range(5):
                call(f"/api/compilations/{job_id}/file", query="token=bad")
            paused, _, _ = call("/api/session", headers={"Authorization": f"Bearer {_SECRET}"})
        self.assertEqual(still_allowed, 200)
        self.assertEqual(paused, 429)

    def test_non_ascii_file_tokens_are_refused_and_counted(self) -> None:
        job_id = uuid.uuid4().hex
        with patch.object(settings, "password", _SECRET):
            refused = [
                call(f"/api/compilations/{job_id}/file", query="token=%C3%A9")[0]
                for _ in range(5)
            ]
            paused, _, _ = call("/api/session", headers={"Authorization": f"Bearer {_SECRET}"})
        self.assertEqual(refused, [401] * 5)
        self.assertEqual(paused, 429)

    def test_the_right_password_clears_earlier_failures(self) -> None:
        wrong = {"Authorization": "Bearer nope"}
        right = {"Authorization": f"Bearer {_SECRET}"}
        with patch.object(settings, "password", _SECRET):
            for _ in range(4):
                call("/api/session", headers=wrong)
            call("/api/session", headers=right)
            after_reset = [call("/api/session", headers=wrong)[0] for _ in range(4)]
        self.assertEqual(after_reset, [401] * 4)

    def test_hosted_server_throttles_by_the_last_forwarded_address(self) -> None:
        def guess(forwarded: str) -> int:
            headers = {"Authorization": "Bearer nope", "X-Forwarded-For": forwarded}
            return call("/api/session", headers=headers)[0]

        with patch.object(settings, "password", _SECRET), patch.object(settings, "hosted", True):
            # The caller controls the first entries, so rotating them must not help.
            statuses = [guess(f"203.0.113.{n}, 198.51.100.7") for n in range(6)]
            other, _, _ = call(
                "/api/session",
                headers={"Authorization": "Bearer nope", "X-Forwarded-For": "198.51.100.8"},
            )
        self.assertEqual(statuses, [401] * 5 + [429])
        self.assertEqual(other, 401)

    def test_file_token_does_not_depend_on_the_password(self) -> None:
        job_id = uuid.uuid4().hex
        with patch.object(settings, "password", _SECRET):
            first = file_token(job_id)
        with patch.object(settings, "password", "a different long password"):
            second = file_token(job_id)
        self.assertEqual(first, second)
        expected = hmac.new(_SECRET.encode(), f"file:{job_id}".encode(), hashlib.sha256)
        self.assertNotEqual(first, expected.hexdigest())

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
        with (
            patch.object(settings, "hosted", True),
            patch.object(settings, "password", "short"),
            self.assertRaisesRegex(ConfigurationError, "at least 12 characters"),
        ):
            require_password_when_hosted()
        with patch.object(settings, "hosted", True), patch.object(settings, "password", _SECRET):
            require_password_when_hosted()
        with patch.object(settings, "hosted", False), patch.object(settings, "password", "short"):
            require_password_when_hosted()
        with patch.object(settings, "hosted", False), patch.object(settings, "password", None):
            require_password_when_hosted()


if __name__ == "__main__":
    unittest.main()
