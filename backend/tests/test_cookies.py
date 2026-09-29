import os
import unittest
from unittest.mock import patch

from app.services.ytdlp_service import _browser_name, _cookies_args


class CookieSelectionTests(unittest.TestCase):
    def test_no_cookies_by_default(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            self.assertIsNone(_browser_name())
            self.assertEqual(_cookies_args(), [])

    def test_browser_flag(self) -> None:
        with patch.dict(os.environ, {"YTDLP_COOKIES_BROWSER": "chrome"}, clear=True):
            self.assertEqual(_cookies_args(), ["--cookies-from-browser", "chrome"])

    def test_browser_can_be_turned_off(self) -> None:
        with patch.dict(os.environ, {"YTDLP_COOKIES_BROWSER": "none"}, clear=True):
            self.assertIsNone(_browser_name())
            self.assertEqual(_cookies_args(), [])

    def test_cookie_file_wins_over_browser(self) -> None:
        with patch.dict(
            os.environ,
            {"YTDLP_COOKIES_BROWSER": "chrome", "YTDLP_COOKIES_FILE": __file__},
            clear=True,
        ):
            args = _cookies_args()
        self.assertEqual(args[:1], ["--cookies"])
        self.assertNotIn("--cookies-from-browser", args)


if __name__ == "__main__":
    unittest.main()
