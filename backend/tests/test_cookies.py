import os
import stat
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

from app.youtube.cookies import (
    _browser_name,
    _cookiefile,
    _deno_path,
    _with_cookies,
    private_cookies,
)

_DENO = "/opt/homebrew/bin/deno"


class CookieSelectionTests(unittest.TestCase):
    def test_no_cookies_by_default(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            self.assertIsNone(_browser_name())
            self.assertEqual(_with_cookies({}), {})

    def test_browser_flag(self) -> None:
        with (
            patch.dict(os.environ, {"YTDLP_COOKIES_BROWSER": "chrome"}, clear=True),
            patch("app.youtube.cookies._deno_path", return_value=_DENO),
        ):
            options = _with_cookies({})
        self.assertEqual(
            options,
            {
                "cookiesfrombrowser": ("chrome",),
                "js_runtimes": {"deno": {"path": _DENO}},
                "remote_components": ["ejs:github"],
            },
        )

    def test_browser_can_be_turned_off(self) -> None:
        with patch.dict(os.environ, {"YTDLP_COOKIES_BROWSER": "none"}, clear=True):
            self.assertIsNone(_browser_name())
            self.assertEqual(_with_cookies({}), {})

    def test_cookie_file_wins_over_browser(self) -> None:
        with (
            patch.dict(
                os.environ,
                {"YTDLP_COOKIES_BROWSER": "chrome", "YTDLP_COOKIES_FILE": __file__},
                clear=True,
            ),
            patch("app.youtube.cookies._deno_path", return_value=_DENO),
        ):
            options = _with_cookies({})
        self.assertEqual(options["cookiefile"], __file__)
        self.assertNotIn("cookiesfrombrowser", options)
        self.assertEqual(options["js_runtimes"], {"deno": {"path": _DENO}})
        self.assertEqual(options["remote_components"], ["ejs:github"])

    def test_login_without_deno_fails_clearly(self) -> None:
        with (
            patch.dict(os.environ, {"YTDLP_COOKIES_BROWSER": "chrome"}, clear=True),
            patch("app.youtube.cookies._deno_path", return_value=None),
            self.assertRaises(RuntimeError) as raised,
        ):
            _with_cookies({})
        self.assertIn("Deno", str(raised.exception))

    @unittest.skipIf(sys.platform == "win32", "Homebrew locations are searched on macOS and Linux")
    def test_deno_path_finds_homebrew_when_missing_from_path(self) -> None:
        def access(path: object, _mode: int) -> bool:
            return str(path) == _DENO

        with (
            patch.dict(os.environ, {}, clear=True),
            patch("app.youtube.cookies.shutil.which", return_value=None),
            patch("app.youtube.cookies.os.access", side_effect=access),
            patch("app.youtube.cookies.os.path.isdir", return_value=False),
        ):
            self.assertEqual(_deno_path(), _DENO)


class PrivateCookieTests(unittest.TestCase):
    def test_each_run_gets_its_own_copy_that_is_removed(self) -> None:
        options = {"cookiefile": __file__, "quiet": True}
        with private_cookies(options) as first, private_cookies(options) as second:
            self.assertNotEqual(first["cookiefile"], __file__)
            self.assertNotEqual(first["cookiefile"], second["cookiefile"])
            self.assertEqual(Path(first["cookiefile"]).read_bytes(), Path(__file__).read_bytes())
            self.assertTrue(first["quiet"])
        self.assertFalse(Path(first["cookiefile"]).exists())
        self.assertFalse(Path(second["cookiefile"]).exists())
        self.assertEqual(options["cookiefile"], __file__)

    def test_no_cookie_file_passes_options_through(self) -> None:
        options = {"quiet": True}
        with private_cookies(options) as run:
            self.assertIs(run, options)

    def test_env_cookies_are_written_once_and_owner_only(self) -> None:
        body = "# Netscape HTTP Cookie File\n.youtube.com\tTRUE\t/\tTRUE\t0\tSID\tredacted"
        with patch.dict(os.environ, {"YTDLP_COOKIES": body}, clear=True):
            first = _cookiefile()
            second = _cookiefile()
        assert first is not None
        self.assertEqual(first, second)
        self.assertIn(".youtube.com", Path(first).read_text(encoding="utf-8"))
        if sys.platform != "win32":
            self.assertEqual(stat.S_IMODE(os.stat(first).st_mode), 0o600)

    def test_env_cookie_file_is_removed_at_exit(self) -> None:
        body = "# Netscape HTTP Cookie File\n.youtube.com\tTRUE\t/\tTRUE\t0\tSID\tcleanup-test"
        with (
            patch.dict(os.environ, {"YTDLP_COOKIES": body}, clear=True),
            patch("app.youtube.cookies.atexit.register") as register,
        ):
            path = _cookiefile()
            self.assertEqual(_cookiefile(), path)
        assert path is not None
        register.assert_called_once()
        cleanup, registered_path = register.call_args.args
        self.assertEqual(registered_path, path)
        self.assertTrue(Path(path).is_file())
        cleanup(registered_path)
        self.assertFalse(Path(path).exists())
        # A second run at exit, after the file is gone, does not raise.
        cleanup(registered_path)


if __name__ == "__main__":
    unittest.main()
