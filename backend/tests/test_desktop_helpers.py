import os
import tempfile
import time
import unittest
import urllib.error
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from fastapi import FastAPI

from app.desktop import browser, paths, server
from app.errors import ConfigurationError


class DetectBrowserTests(unittest.TestCase):
    def test_mac_picks_the_first_installed_browser(self) -> None:
        installed = {Path("/Applications/Firefox.app"), Path("/Applications/Safari.app")}
        with (
            patch.object(browser, "sys", SimpleNamespace(platform="darwin")),
            patch.object(Path, "exists", lambda path: path in installed),
        ):
            self.assertEqual(browser.detect_browser(), "firefox")

    def test_windows_uses_a_firefox_profile(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "Mozilla" / "Firefox" / "Profiles").mkdir(parents=True)
            with (
                patch.object(browser, "sys", SimpleNamespace(platform="win32")),
                patch.dict(os.environ, {"APPDATA": tmp}),
            ):
                self.assertEqual(browser.detect_browser(), "firefox")

    def test_windows_skips_chromium_browsers(self) -> None:
        # Their app-bound cookie encryption makes yt-dlp fail to load cookies.
        with tempfile.TemporaryDirectory() as tmp:
            edge = Path(tmp) / "x86" / "Microsoft" / "Edge" / "Application" / "msedge.exe"
            edge.parent.mkdir(parents=True)
            edge.write_bytes(b"")
            env = {
                "APPDATA": str(Path(tmp) / "roaming"),
                "LOCALAPPDATA": str(Path(tmp) / "local"),
                "PROGRAMFILES": str(Path(tmp) / "pf"),
                "PROGRAMFILES(X86)": str(Path(tmp) / "x86"),
            }
            with (
                patch.object(browser, "sys", SimpleNamespace(platform="win32")),
                patch.dict(os.environ, env),
            ):
                self.assertIsNone(browser.detect_browser())

    def test_nothing_installed_returns_none(self) -> None:
        with (
            patch.object(browser, "sys", SimpleNamespace(platform="darwin")),
            patch.object(Path, "exists", return_value=False),
        ):
            self.assertIsNone(browser.detect_browser())

    def test_other_platforms_return_none(self) -> None:
        with patch.object(browser, "sys", SimpleNamespace(platform="linux")):
            self.assertIsNone(browser.detect_browser())


class AppSupportDirTests(unittest.TestCase):
    def _dir(self, platform: str, home: Path, appdata: str | None = None) -> Path:
        with (
            patch.object(paths, "sys", SimpleNamespace(platform=platform)),
            patch.object(Path, "home", return_value=home),
            patch.dict(os.environ),
        ):
            os.environ.pop("APPDATA", None)
            if appdata is not None:
                os.environ["APPDATA"] = appdata
            return paths.app_support_dir()

    def test_mac_uses_application_support(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = self._dir("darwin", Path(tmp))
            self.assertEqual(base, Path(tmp) / "Library" / "Application Support" / "CompCreator")
            self.assertTrue(base.is_dir())

    def test_windows_uses_appdata(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = self._dir("win32", Path(tmp), str(Path(tmp) / "Roam"))
            self.assertEqual(base, Path(tmp) / "Roam" / "CompCreator")

    def test_windows_without_appdata_falls_back_to_home(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = self._dir("win32", Path(tmp))
            self.assertEqual(base, Path(tmp) / "AppData" / "Roaming" / "CompCreator")

    def test_linux_uses_a_dot_folder(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(self._dir("linux", Path(tmp)), Path(tmp) / ".compcreator")

    def test_file_in_the_way_is_a_configuration_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / ".compcreator").write_text("", encoding="utf-8")
            with self.assertRaises(ConfigurationError):
                self._dir("linux", Path(tmp))


class BundleDirTests(unittest.TestCase):
    def test_source_checkout_adds_nothing(self) -> None:
        with patch.object(paths, "sys", SimpleNamespace()):
            self.assertEqual(paths.bundle_dirs(), [])

    def test_frozen_app_searches_beside_the_executable(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            contents = Path(tmp).resolve() / "Contents"
            (contents / "MacOS").mkdir(parents=True)
            (contents / "Resources").mkdir()
            frozen = SimpleNamespace(
                frozen=True,
                executable=str(contents / "MacOS" / "CompCreator"),
                _MEIPASS=str(contents / "Frameworks"),
            )
            with patch.object(paths, "sys", frozen):
                dirs = paths.bundle_dirs()
        self.assertEqual(
            dirs,
            [contents / "MacOS", contents / "Frameworks", contents / "Resources"],
        )

    def test_frozen_static_dir_reads_the_extracted_bundle(self) -> None:
        with patch.object(paths, "sys", SimpleNamespace(frozen=True, _MEIPASS="/bundle")):
            self.assertEqual(paths.static_dir(), Path("/bundle") / "frontend")

    def test_frozen_static_dir_without_bundle_is_an_error(self) -> None:
        with (
            patch.object(paths, "sys", SimpleNamespace(frozen=True)),
            self.assertRaises(ConfigurationError),
        ):
            paths.static_dir()


class PrepareEnvironmentTests(unittest.TestCase):
    def _prepare(
        self, env: dict[str, str], browser_name: str | None
    ) -> tuple[Path, dict[str, str]]:
        with tempfile.TemporaryDirectory() as tmp:
            support = Path(tmp)
            with (
                patch.dict(os.environ, env, clear=True),
                patch.object(server, "app_support_dir", return_value=support),
                patch.object(server, "bundle_dirs", return_value=[Path("/bundle")]),
                patch.object(server, "detect_browser", return_value=browser_name),
            ):
                log_path = server.prepare_environment()
                self.assertEqual(log_path, support / "desktop.log")
                return support, dict(os.environ)

    def test_fills_defaults_and_prepends_bundle_to_path(self) -> None:
        support, env = self._prepare({"PATH": "/usr/bin"}, "chrome")
        self.assertEqual(env["COMPCREATOR_DESKTOP"], "1")
        self.assertEqual(env["JOBS_DIR"], str(support / "jobs"))
        self.assertEqual(env["PATH"], str(Path("/bundle")) + os.pathsep + "/usr/bin")
        self.assertEqual(env["YTDLP_COOKIES_BROWSER"], "chrome")

    def test_no_browser_is_recorded_as_none(self) -> None:
        _, env = self._prepare({}, None)
        self.assertEqual(env["YTDLP_COOKIES_BROWSER"], "none")

    def test_explicit_cookies_skip_browser_detection(self) -> None:
        _, env = self._prepare({"YTDLP_COOKIES_FILE": "/c.txt", "JOBS_DIR": "/mine"}, "chrome")
        self.assertNotIn("YTDLP_COOKIES_BROWSER", env)
        self.assertEqual(env["JOBS_DIR"], "/mine")


class LocalServerTests(unittest.TestCase):
    def test_free_port_is_a_real_port(self) -> None:
        port = server._free_port()
        self.assertGreater(port, 0)
        self.assertLess(port, 65536)

    def test_mount_ui_serves_the_folder_at_the_root(self) -> None:
        application = FastAPI()
        with tempfile.TemporaryDirectory() as tmp:
            server.mount_ui(application, Path(tmp))
        route = application.routes[-1]
        self.assertEqual(getattr(route, "name", None), "ui")
        self.assertEqual(getattr(route, "path", None), "")

    def test_wait_returns_once_health_answers(self) -> None:
        ok = MagicMock()
        ok.__enter__.return_value.status = 200
        attempts = [urllib.error.URLError("refused"), ok]
        with (
            patch.object(server.urllib.request, "urlopen", side_effect=attempts) as urlopen,
            patch.object(server, "time", SimpleNamespace(time=time.time, sleep=lambda _s: None)),
        ):
            server._wait_until_ready("http://127.0.0.1:1/api/health", timeout=5)
        self.assertEqual(urlopen.call_count, 2)

    def test_wait_gives_up_with_one_sentence(self) -> None:
        clock = iter([0.0, 0.0, 10.0])
        # Replace only server's reference: logging also reads time.time().
        fake_time = SimpleNamespace(time=lambda: next(clock), sleep=lambda _seconds: None)
        with (
            patch.object(server.urllib.request, "urlopen", side_effect=OSError("refused")),
            patch.object(server, "time", fake_time),
            self.assertLogs("compcreator.desktop", level="ERROR"),
            self.assertRaises(ConfigurationError) as caught,
        ):
            server._wait_until_ready("http://127.0.0.1:1/api/health", timeout=1)
        self.assertIn("local server did not start", str(caught.exception))


if __name__ == "__main__":
    unittest.main()
