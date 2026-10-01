import contextlib
import subprocess
import tempfile
import unittest
from collections.abc import Callable
from pathlib import Path
from typing import Any
from unittest.mock import Mock, patch

import yt_dlp

from app.errors import ConfigurationError
from app.jobs.runner import JobCancelled
from app.youtube import download
from app.youtube.client import _run_ytdlp, _ytdlp_options
from app.youtube.formats import _format_selector


def _done(returncode: int = 0, stderr: str = "") -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess(["ffmpeg"], returncode, "", stderr)


def _writes(*suffixes: str) -> Callable[[dict[str, Any], str], None]:
    """A ``_run_ytdlp`` stand-in that creates files from the output template."""

    def _fake(options: dict[str, Any], _url: str) -> None:
        stem = options["outtmpl"].removesuffix(".%(ext)s")
        for suffix in suffixes:
            Path(stem + suffix).write_bytes(b"media")

    return _fake


def _no_cookies(options: dict[str, Any]) -> dict[str, Any]:
    return options


class FormatSelectorTests(unittest.TestCase):
    def test_hd_caps_at_1080p(self) -> None:
        selector = _format_selector(False)
        self.assertIn("height<=1080", selector)
        self.assertNotIn("2160", selector)

    def test_4k_caps_at_2160p(self) -> None:
        selector = _format_selector(True)
        self.assertIn("height<=2160", selector)
        self.assertTrue(selector.endswith("/b"))


class ClientTests(unittest.TestCase):
    def test_extra_options_override_defaults(self) -> None:
        with patch("app.youtube.client._with_cookies", side_effect=_no_cookies):
            options = _ytdlp_options("out.%(ext)s", False, {"quiet": False, "extra": 1})
        self.assertFalse(options["quiet"])
        self.assertEqual(options["extra"], 1)
        self.assertEqual(options["outtmpl"], "out.%(ext)s")
        self.assertEqual(options["merge_output_format"], "mp4")

    def _run_with(self, error: BaseException | None) -> dict[str, Any]:
        seen: dict[str, Any] = {}

        class _FakeYDL:
            def __init__(self, options: dict[str, Any]) -> None:
                seen["options"] = options

            def __enter__(self) -> "_FakeYDL":
                return self

            def __exit__(self, *_args: object) -> None:
                return None

            def download(self, urls: list[str]) -> None:
                seen["urls"] = urls
                if error is not None:
                    raise error

        with (
            patch("app.youtube.client.yt_dlp.YoutubeDL", _FakeYDL),
            patch("app.youtube.client.private_cookies", side_effect=contextlib.nullcontext),
        ):
            _run_ytdlp({}, "https://www.youtube.com/watch?v=abcdefghijk")
        return seen

    def test_download_installs_a_cancel_checkpoint_hook(self) -> None:
        seen = self._run_with(None)
        self.assertEqual(seen["urls"], ["https://www.youtube.com/watch?v=abcdefghijk"])
        [hook] = seen["options"]["progress_hooks"]
        with patch("app.youtube.client.runner.checkpoint") as checkpoint:
            hook({"status": "downloading"})
        checkpoint.assert_called_once()

    def test_cancel_passes_through(self) -> None:
        with self.assertRaises(JobCancelled):
            self._run_with(JobCancelled())

    def test_ytdlp_error_becomes_a_runtime_error_tail(self) -> None:
        error = yt_dlp.utils.DownloadError("x" * 900 + "Video unavailable")
        with self.assertRaises(RuntimeError) as caught:
            self._run_with(error)
        self.assertEqual(len(str(caught.exception)), 800)
        self.assertTrue(str(caught.exception).endswith("Video unavailable"))

    def test_empty_ytdlp_error_has_a_sentence(self) -> None:
        with self.assertRaises(RuntimeError) as caught:
            self._run_with(yt_dlp.utils.DownloadError("  "))
        self.assertEqual(str(caught.exception), "yt-dlp failed")

    def test_os_error_becomes_one_sentence(self) -> None:
        denied = PermissionError(13, "Permission denied", "/tmp/clip.mp4")
        with self.assertRaises(RuntimeError) as caught:
            self._run_with(denied)
        self.assertEqual(str(caught.exception), "Permission denied for /tmp/clip.mp4.")


class DownloadRoutingTests(unittest.TestCase):
    def test_missing_or_zero_duration_downloads_the_whole_file(self) -> None:
        self.assertTrue(download.use_concurrent_download(0, 10, 0))
        self.assertTrue(download.use_concurrent_download(0, 10, -5))

    def test_short_slice_of_long_video_uses_sections(self) -> None:
        with (
            patch.object(download, "_download_with_sections", return_value=Path("s")) as sections,
            patch.object(download, "_download_full_then_trim") as full,
        ):
            result = download.download_section(
                "abcdefghijk", 3600, 3660, Path("clip"), duration_seconds=4 * 3600
            )
        self.assertEqual(result, Path("s"))
        full.assert_not_called()
        sections.assert_called_once_with("abcdefghijk", 3600, 3660, Path("clip"), False)

    def test_large_slice_uses_full_download(self) -> None:
        with (
            patch.object(download, "_download_with_sections") as sections,
            patch.object(download, "_download_full_then_trim", return_value=Path("f")) as full,
        ):
            result = download.download_section(
                "abcdefghijk", 0, 60, Path("clip"), output_4k=True, duration_seconds=90
            )
        self.assertEqual(result, Path("f"))
        sections.assert_not_called()
        full.assert_called_once_with("abcdefghijk", 0, 60, Path("clip"), True)


class SectionDownloadTests(unittest.TestCase):
    def test_section_download_returns_the_media_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            stem = Path(tmp) / "clip_000"
            with (
                patch("app.youtube.client._with_cookies", side_effect=_no_cookies),
                patch.object(download, "_run_ytdlp", side_effect=_writes(".part", ".webm")) as run,
            ):
                result = download._download_with_sections("abcdefghijk", 5, 10, stem, False)
            self.assertEqual(result, stem.with_suffix(".webm"))
        options = run.call_args.args[0]
        self.assertIn("download_ranges", options)

    def test_no_media_file_is_an_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            stem = Path(tmp) / "clip_000"
            (Path(tmp) / "clip_000.part").write_bytes(b"")
            with self.assertRaises(RuntimeError) as caught:
                download._find_download(stem)
        self.assertIn("clip_000", str(caught.exception))


class FullThenTrimTests(unittest.TestCase):
    def _call(
        self,
        tmp: str,
        *,
        start: float,
        end: float,
        duration: float | None,
        run: Callable[[list[str]], subprocess.CompletedProcess[str]],
    ) -> Path:
        stem = Path(tmp) / "clip_000"
        with (
            patch("app.youtube.client._with_cookies", side_effect=_no_cookies),
            patch.object(download, "_run_ytdlp", side_effect=_writes(".mp4")),
            patch.object(download, "_probe_duration", return_value=duration),
            patch.object(download.runner, "run", run),
        ):
            return download._download_full_then_trim("abcdefghijk", start, end, stem, False)

    def test_whole_video_is_renamed_without_ffmpeg(self) -> None:
        run = Mock()
        with tempfile.TemporaryDirectory() as tmp:
            result = self._call(tmp, start=0, end=119.8, duration=120, run=run)
            self.assertEqual(result, Path(tmp) / "clip_000.mp4")
            self.assertEqual([p.name for p in Path(tmp).iterdir()], ["clip_000.mp4"])
        run.assert_not_called()

    def test_slice_is_trimmed_and_full_file_removed(self) -> None:
        run = Mock(return_value=_done())
        with tempfile.TemporaryDirectory() as tmp:
            result = self._call(tmp, start=10, end=25, duration=120, run=run)
            self.assertEqual(result, Path(tmp) / "clip_000.mp4")
            self.assertFalse((Path(tmp) / "clip_000_full.mp4").exists())
        command = run.call_args.args[0]
        self.assertEqual(command[command.index("-ss") + 1], "10.000")
        self.assertEqual(command[command.index("-t") + 1], "15.000")

    def test_unknown_duration_still_trims(self) -> None:
        run = Mock(return_value=_done())
        with tempfile.TemporaryDirectory() as tmp:
            self._call(tmp, start=0, end=30, duration=None, run=run)
        run.assert_called_once()

    def test_trim_failure_removes_partial_output(self) -> None:
        def _fail(command: list[str]) -> subprocess.CompletedProcess[str]:
            Path(command[-1]).write_bytes(b"partial")
            return _done(1, stderr="Invalid data\n")

        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(RuntimeError) as caught:
                self._call(tmp, start=10, end=20, duration=120, run=_fail)
            self.assertEqual(list(Path(tmp).iterdir()), [])
        self.assertEqual(str(caught.exception), "Invalid data")

    def test_missing_ffmpeg_is_a_configuration_error(self) -> None:
        run = Mock(side_effect=FileNotFoundError())
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ConfigurationError):
                self._call(tmp, start=10, end=20, duration=120, run=run)
            self.assertEqual(list(Path(tmp).iterdir()), [])


if __name__ == "__main__":
    unittest.main()
