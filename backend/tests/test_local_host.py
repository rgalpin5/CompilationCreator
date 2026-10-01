import unittest
from unittest.mock import patch

from app.config import settings
from app.local_host import host_name
from tests.asgi import call


def _status(host: str | None) -> int:
    headers = {"Host": host} if host is not None else None
    return call("/api/session", headers=headers)[0]


class HostNameTests(unittest.TestCase):
    def test_strips_ports_and_brackets(self) -> None:
        self.assertEqual(host_name("localhost:8000"), "localhost")
        self.assertEqual(host_name("127.0.0.1"), "127.0.0.1")
        self.assertEqual(host_name("[::1]:8000"), "::1")
        self.assertEqual(host_name("Evil.Example:80"), "evil.example")


class LocalHostMiddlewareTests(unittest.TestCase):
    def test_open_local_server_answers_only_loopback_names(self) -> None:
        with patch.object(settings, "hosted", False), patch.object(settings, "password", None):
            for host in ("localhost:8000", "127.0.0.1:51234", "[::1]:8000", None):
                with self.subTest(host=host):
                    self.assertEqual(_status(host), 200)
            self.assertEqual(_status("attacker.example:8000"), 400)
            self.assertEqual(_status("192.168.1.20:8000"), 400)

    def test_password_or_hosting_turns_the_check_off(self) -> None:
        with patch.object(settings, "hosted", True), patch.object(settings, "password", None):
            self.assertEqual(_status("compcreator-api.a.run.app"), 200)
        with patch.object(settings, "hosted", False), patch.object(settings, "password", "x" * 16):
            # The password check answers instead, with 401 for a request without it.
            self.assertEqual(_status("192.168.1.20:8000"), 401)


if __name__ == "__main__":
    unittest.main()
