import os
import unittest
from unittest.mock import patch

from app.services.ytdlp_service import _browser_name, _with_cookies


class CookieSelectionTests(unittest.TestCase):
    def test_no_cookies_by_default(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            self.assertIsNone(_browser_name())
            self.assertEqual(_with_cookies({}), {})

    def test_browser_flag(self) -> None:
        with patch.dict(os.environ, {"YTDLP_COOKIES_BROWSER": "chrome"}, clear=True):
            self.assertEqual(_with_cookies({}), {"cookiesfrombrowser": ("chrome",)})

    def test_browser_can_be_turned_off(self) -> None:
        with patch.dict(os.environ, {"YTDLP_COOKIES_BROWSER": "none"}, clear=True):
            self.assertIsNone(_browser_name())
            self.assertEqual(_with_cookies({}), {})

    def test_cookie_file_wins_over_browser(self) -> None:
        with patch.dict(
            os.environ,
            {"YTDLP_COOKIES_BROWSER": "chrome", "YTDLP_COOKIES_FILE": __file__},
            clear=True,
        ):
            options = _with_cookies({})
        self.assertEqual(options["cookiefile"], __file__)
        self.assertNotIn("cookiesfrombrowser", options)


if __name__ == "__main__":
    unittest.main()
