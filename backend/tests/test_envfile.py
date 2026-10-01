import os
import tempfile
import unittest
from pathlib import Path

from app.envfile import load_env_file


class EnvFileTests(unittest.TestCase):
    def test_missing_file_is_ignored(self) -> None:
        environ: dict[str, str] = {}
        load_env_file(Path(tempfile.gettempdir()) / "compcreator-missing.env", environ)
        self.assertEqual(environ, {})

    def test_assignments_comments_and_quotes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / ".env"
            path.write_text(
                "\n".join(
                    [
                        "# comment",
                        "",
                        "CORS_ORIGINS=http://localhost:3000",
                        "export JOBS_DIR=/tmp/jobs",
                        'YTDLP_DENO="/usr/local/bin/deno"',
                        "YTDLP_COOKIES='a=b; c=d'",
                        "NOT AN ASSIGNMENT",
                        "1BAD=value",
                        "EMPTY=",
                    ]
                ),
                encoding="utf-8",
            )
            environ: dict[str, str] = {}
            load_env_file(path, environ)

        self.assertEqual(
            environ,
            {
                "CORS_ORIGINS": "http://localhost:3000",
                "JOBS_DIR": "/tmp/jobs",
                "YTDLP_DENO": "/usr/local/bin/deno",
                "YTDLP_COOKIES": "a=b; c=d",
                "EMPTY": "",
            },
        )

    def test_existing_values_win(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / ".env"
            path.write_text("CORS_ORIGINS=http://example.test\n", encoding="utf-8")
            environ = {"CORS_ORIGINS": "http://localhost:3000"}
            load_env_file(path, environ)
        self.assertEqual(environ["CORS_ORIGINS"], "http://localhost:3000")

    def test_loader_accepts_os_environ(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / ".env"
            path.write_text("COMPCREATOR_ENVFILE_TEST=1\n", encoding="utf-8")
            previous = os.environ.pop("COMPCREATOR_ENVFILE_TEST", None)
            try:
                load_env_file(path, os.environ)
                self.assertEqual(os.environ["COMPCREATOR_ENVFILE_TEST"], "1")
            finally:
                os.environ.pop("COMPCREATOR_ENVFILE_TEST", None)
                if previous is not None:
                    os.environ["COMPCREATOR_ENVFILE_TEST"] = previous
