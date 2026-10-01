"""What a hosted server shows to callers that have not sent the password."""

import os
import subprocess
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

from app.config import settings
from app.main import _file_message

_BACKEND = Path(__file__).resolve().parents[1]


class HostedDocsTests(unittest.TestCase):
    def test_hosted_server_does_not_publish_its_docs_but_can_still_build_the_schema(self) -> None:
        env = {**os.environ, "K_SERVICE": "compcreator-api", "PYTHONPATH": str(_BACKEND)}
        env.pop("VERCEL", None)
        script = (
            "from app.main import app\n"
            "print(app.docs_url, app.redoc_url, app.openapi_url)\n"
            "print(bool(app.openapi()['paths']))\n"
        )
        result = subprocess.run(
            [sys.executable, "-c", script],
            cwd=_BACKEND,
            env=env,
            capture_output=True,
            text=True,
            check=True,
        )
        self.assertEqual(result.stdout.split(), ["None", "None", "None", "True"])

    def test_local_server_keeps_its_docs(self) -> None:
        from app.main import app

        if settings.hosted:
            self.skipTest("this test process runs as a hosted server")
        self.assertEqual(app.openapi_url, "/openapi.json")


class FileMessageTests(unittest.TestCase):
    def test_hosted_server_names_the_file_but_not_its_folder(self) -> None:
        path = str(Path("/srv") / "secret-folder" / "clip.mp4")
        exc = FileNotFoundError(2, "No such file or directory", path)
        with patch.object(settings, "hosted", True):
            hosted = _file_message(exc)
        with patch.object(settings, "hosted", False):
            local = _file_message(exc)
        self.assertEqual(hosted, "Could not find clip.mp4.")
        self.assertIn("secret-folder", local)


if __name__ == "__main__":
    unittest.main()
