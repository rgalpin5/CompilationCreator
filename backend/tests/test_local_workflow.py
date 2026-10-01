"""List a channel, export a timeline, and save the file on this machine.

YouTube and ffmpeg are replaced. Job folders and the usage log live in a
temporary directory, and cookie settings from the developer environment are
cleared so the test cannot read a browser profile or write a cookie file.
"""

import asyncio
import contextlib
import os
import subprocess
import tempfile
import threading
import time
import unittest
from collections.abc import Iterator
from pathlib import Path
from typing import Any, ClassVar
from unittest.mock import patch

from fastapi import BackgroundTasks

from app.jobs.runner import runner
from app.jobs.store import JobStore
from app.media.probe import StreamLayout
from app.models import ChannelRequest, Clip, CompilationRequest, DownloadRequest
from app.routers import channels, compilations
from app.routers import usage as usage_routes
from app.usage.store import UsageStore

_LAYOUT = StreamLayout(
    "h264",
    1920,
    1080,
    "yuv420p",
    "30/1",
    "1/15360",
    "High",
    "aac",
    "44100",
    2,
    "1/44100",
)

_INTRO = "abcdefghijk"
_OUTRO = "abcdefghijl"


class _OfflineYoutubeDL:
    """A client that must not be asked to talk to YouTube."""

    def __init__(self, options: dict[str, Any]) -> None:
        self.options = options

    def __enter__(self) -> "_OfflineYoutubeDL":
        return self

    def __exit__(self, _exc_type: object, _exc: object, _tb: object) -> None:
        return None

    def extract_info(self, url: str, download: bool = False) -> dict[str, Any]:
        raise AssertionError(f"YouTube extract was attempted for {url}")

    def download(self, urls: list[str]) -> None:
        raise AssertionError(f"YouTube download was attempted for {urls}")


class _ChannelCatalog(_OfflineYoutubeDL):
    """One local page of channel videos. ``download=True`` is still refused."""

    urls: ClassVar[list[str]] = []

    def extract_info(self, url: str, download: bool = False) -> dict[str, Any]:
        if download:
            raise AssertionError(f"channel listing tried to download {url}")
        type(self).urls.append(url)
        return {
            "channel": "Some channel",
            "entries": [
                _entry(_INTRO, "Intro", 90, 10),
                _entry(_OUTRO, "Outro", 120, 20),
            ],
        }


def _entry(video_id: str, title: str, duration: int, views: int) -> dict[str, Any]:
    return {
        "id": video_id,
        "title": title,
        "duration": duration,
        "view_count": views,
        "url": f"https://www.youtube.com/watch?v={video_id}",
    }


def _local_media_tool(command: list[str]) -> subprocess.CompletedProcess[str]:
    """Stand in for ffmpeg and ffprobe without starting either program."""
    if not command:
        raise AssertionError("empty media command")
    program = Path(command[0]).name
    if program == "ffprobe":
        return subprocess.CompletedProcess(command, 0, stdout="0\n", stderr="")
    if program != "ffmpeg":
        raise AssertionError(f"refusing to start {program}")
    if "-i" not in command:
        raise AssertionError("ffmpeg command has no input")
    source = Path(command[command.index("-i") + 1])
    dest = Path(command[-1])
    dest.write_bytes(source.read_bytes() if source.is_file() else b"")
    return subprocess.CompletedProcess(command, 0, stdout="", stderr="")


def _refuse_ffprobe(*_args: object, **_kwargs: object) -> subprocess.CompletedProcess[str]:
    raise AssertionError("ffprobe was started")


def _same_layout(_path: Path) -> StreamLayout:
    return _LAYOUT


def _fake_download(
    video_id: str,
    start: float,
    end: float,
    dest_stem: Path,
    *,
    output_4k: bool = False,
    duration_seconds: int | None = None,
) -> Path:
    path = dest_stem.parent / f"{dest_stem.name}.mp4"
    path.write_bytes(f"{video_id} {int(start)}-{int(end)}".encode())
    return path


def _fail_download(
    video_id: str,
    start: float,
    end: float,
    dest_stem: Path,
    *,
    output_4k: bool = False,
    duration_seconds: int | None = None,
) -> Path:
    raise RuntimeError("yt-dlp failed")


@contextlib.contextmanager
def _quiet_network() -> Iterator[None]:
    """Drop cookie settings and refuse a real YoutubeDL or ffprobe process."""
    hidden = {
        "YTDLP_COOKIES": "",
        "YTDLP_COOKIES_FILE": "",
        "YTDLP_COOKIES_BROWSER": "none",
    }
    with (
        patch.dict(os.environ, hidden),
        patch("app.youtube.client.yt_dlp.YoutubeDL", _OfflineYoutubeDL),
        patch("app.media.probe.subprocess.run", _refuse_ffprobe),
        patch.object(runner, "run", _local_media_tool),
    ):
        yield


def _run_export(
    jobs: JobStore,
    usage: UsageStore,
    body: CompilationRequest,
) -> str:
    tasks = BackgroundTasks()
    job_id = compilations.create_compilation(body, tasks, jobs, usage).id
    asyncio.run(tasks())
    return job_id


class LocalWorkflowTests(unittest.TestCase):
    def setUp(self) -> None:
        _ChannelCatalog.urls = []

    def test_list_export_save_and_log_stay_inside_the_temp_directory(self) -> None:
        with tempfile.TemporaryDirectory() as tmp, _quiet_network():
            root = Path(tmp)
            jobs = JobStore(root / "jobs")
            usage = UsageStore(root / "usage.json")
            save_to = root / "Downloads"
            save_to.mkdir()

            with patch("app.youtube.listing.yt_dlp.YoutubeDL", _ChannelCatalog):
                page = channels.read_channel(
                    ChannelRequest(url="https://www.youtube.com/@somechannel"),
                    limit=24,
                    offset=0,
                    usage=usage,
                )

            self.assertEqual([video.video_id for video in page.videos], [_INTRO, _OUTRO])
            self.assertFalse(page.has_more)
            self.assertEqual(page.videos[0].compilation_count, 0)
            self.assertEqual(
                _ChannelCatalog.urls,
                ["https://www.youtube.com/@somechannel/videos"],
            )

            intro = page.videos[0]
            outro = page.videos[1]
            with (
                patch("app.compilation.pipeline.download_section", _fake_download),
                patch("app.compilation.pipeline.probe_layout", _same_layout),
            ):
                job_id = _run_export(
                    jobs,
                    usage,
                    CompilationRequest(
                        clips=[
                            Clip(
                                video_id=outro.video_id,
                                title=outro.title,
                                start="0:05",
                                end="0:25",
                                order=1,
                                channel=outro.channel,
                                view_count=outro.view_count,
                                duration_seconds=outro.duration_seconds,
                                thumbnail=outro.thumbnail,
                            ),
                            Clip(
                                video_id=intro.video_id,
                                title=intro.title,
                                start="0:10",
                                end="0:40",
                                order=0,
                                channel=intro.channel,
                                view_count=intro.view_count,
                                duration_seconds=intro.duration_seconds,
                                thumbnail=intro.thumbnail,
                            ),
                        ]
                    ),
                )

            ready = compilations.compilation_status(job_id, jobs)
            self.assertEqual(ready.status, "ready")
            self.assertEqual(ready.progress, "Ready")
            self.assertEqual(ready.download_url, f"/api/compilations/{job_id}/download")
            stored = jobs.get(job_id)
            self.assertIsNotNone(stored)
            assert stored is not None
            job_dir = Path(stored["dir"])
            self.assertEqual((job_dir / "raw_001.mp4").read_bytes(), b"abcdefghijk 10-40")
            self.assertEqual((job_dir / "raw_002.mp4").read_bytes(), b"abcdefghijl 5-25")
            self.assertEqual((job_dir / "part_001.mp4").read_bytes(), b"abcdefghijk 10-40")
            joined = (job_dir / "concat.txt").read_bytes()
            self.assertEqual((job_dir / "compilation.mp4").read_bytes(), joined)

            saved = compilations.download_compilation(
                job_id,
                DownloadRequest(directory=str(save_to)),
                jobs,
            )
            self.assertEqual(saved.status, "saved")
            saved_path = Path(saved.saved_path or "")
            self.assertTrue(saved_path.is_file())
            self.assertEqual(saved_path.parent, save_to.resolve())
            self.assertIn(b"part_001.mp4", saved_path.read_bytes())
            self.assertIn(b"part_002.mp4", saved_path.read_bytes())
            self.assertLess(
                saved_path.read_bytes().index(b"part_001.mp4"),
                saved_path.read_bytes().index(b"part_002.mp4"),
            )
            self.assertFalse(job_dir.exists())
            self.assertEqual(
                [path.resolve() for path in save_to.iterdir()],
                [saved_path.resolve()],
            )

            counts = usage_routes.read_usage(f"{_INTRO},{_OUTRO}", usage)
            self.assertEqual(counts["counts"], {_INTRO: 1, _OUTRO: 1})
            logs = usage_routes.read_logs(usage)
            self.assertEqual(len(logs["compilations"]), 1)
            self.assertEqual(logs["compilations"][0]["clips"], 2)
            self.assertEqual(logs["compilations"][0]["duration_seconds"], 50)
            reloaded = UsageStore(root / "usage.json")
            self.assertEqual(reloaded.count(_INTRO), 1)

            with patch("app.youtube.listing.yt_dlp.YoutubeDL", _ChannelCatalog):
                again = channels.read_channel(
                    ChannelRequest(url="https://www.youtube.com/@somechannel"),
                    limit=24,
                    offset=0,
                    usage=usage,
                )
            self.assertEqual(again.videos[0].compilation_count, 1)

    def test_failed_download_does_not_record_a_compilation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp, _quiet_network():
            root = Path(tmp)
            jobs = JobStore(root / "jobs")
            usage = UsageStore(root / "usage.json")
            with patch("app.compilation.pipeline.download_section", _fail_download):
                job_id = _run_export(
                    jobs,
                    usage,
                    CompilationRequest(
                        clips=[
                            Clip(
                                video_id=_INTRO,
                                title="Intro",
                                start="0:00",
                                end="0:30",
                                order=0,
                            )
                        ]
                    ),
                )

            status = compilations.compilation_status(job_id, jobs)
            self.assertEqual(status.status, "failed")
            self.assertEqual(status.progress, "Failed")
            self.assertIn("yt-dlp failed", status.error or "")
            self.assertIsNone(status.download_url)
            self.assertEqual(usage.logs()["compilations"], [])
            stored = jobs.get(job_id)
            self.assertIsNotNone(stored)
            assert stored is not None
            self.assertFalse(Path(stored["dir"]).exists())

    def test_usage_log_failure_still_finishes_the_export(self) -> None:
        with tempfile.TemporaryDirectory() as tmp, _quiet_network():
            root = Path(tmp)
            jobs = JobStore(root / "jobs")
            usage = UsageStore(root / "usage.json")
            with (
                patch("app.compilation.pipeline.download_section", _fake_download),
                patch("app.compilation.pipeline.probe_layout", _same_layout),
                patch.object(usage, "_save", side_effect=PermissionError("usage.json")),
                self.assertLogs("compcreator.compilation", level="ERROR"),
            ):
                job_id = _run_export(
                    jobs,
                    usage,
                    CompilationRequest(
                        clips=[
                            Clip(
                                video_id=_INTRO,
                                title="Intro",
                                start="0:00",
                                end="0:30",
                                order=0,
                            )
                        ]
                    ),
                )

            status = compilations.compilation_status(job_id, jobs)
            self.assertEqual(status.status, "ready")
            self.assertIsNone(status.error)
            self.assertIsNotNone(status.download_url)

    def test_failed_download_stops_the_other_downloads_first(self) -> None:
        sibling_running = threading.Event()
        sibling_done = threading.Event()

        def download(
            video_id: str,
            start: float,
            end: float,
            dest_stem: Path,
            *,
            output_4k: bool = False,
            duration_seconds: int | None = None,
        ) -> Path:
            if video_id == _INTRO:
                sibling_running.wait(5)
                raise RuntimeError("yt-dlp failed")
            sibling_running.set()
            try:
                # Stands in for an in-process yt-dlp progress hook.
                deadline = time.time() + 5
                while time.time() < deadline:
                    runner.checkpoint()
                    time.sleep(0.01)
                raise AssertionError("sibling download was never stopped")
            finally:
                sibling_done.set()

        with tempfile.TemporaryDirectory() as tmp, _quiet_network():
            root = Path(tmp)
            jobs = JobStore(root / "jobs")
            usage = UsageStore(root / "usage.json")
            with (
                patch("app.compilation.pipeline.download_section", download),
                patch("app.compilation.pipeline.download_workers", return_value=2),
            ):
                job_id = _run_export(
                    jobs,
                    usage,
                    CompilationRequest(
                        clips=[
                            Clip(video_id=_INTRO, title="Intro", start="0:00", end="0:30", order=0),
                            Clip(video_id=_OUTRO, title="Outro", start="0:00", end="0:30", order=1),
                        ]
                    ),
                )

            self.assertTrue(sibling_done.is_set())
            status = compilations.compilation_status(job_id, jobs)
            self.assertEqual(status.status, "failed")
            self.assertIn("yt-dlp failed", status.error or "")
            self.assertFalse(runner.is_cancelled(job_id))

    def test_cancel_during_download_removes_the_job_folder(self) -> None:
        with tempfile.TemporaryDirectory() as tmp, _quiet_network():
            root = Path(tmp)
            jobs = JobStore(root / "jobs")
            usage = UsageStore(root / "usage.json")

            def download(
                video_id: str,
                start: float,
                end: float,
                dest_stem: Path,
                *,
                output_4k: bool = False,
                duration_seconds: int | None = None,
            ) -> Path:
                path = _fake_download(video_id, start, end, dest_stem)
                job_id = dest_stem.parent.name
                compilations.cancel_compilation(job_id, jobs)
                self.assertTrue(path.is_file(), "cancel route deleted files mid-download")
                runner.checkpoint()
                return path

            with patch("app.compilation.pipeline.download_section", download):
                job_id = _run_export(
                    jobs,
                    usage,
                    CompilationRequest(
                        clips=[
                            Clip(video_id=_INTRO, title="Intro", start="0:00", end="0:30", order=0)
                        ]
                    ),
                )

            stored = jobs.get(job_id)
            assert stored is not None
            self.assertEqual(stored["status"], "cancelled")
            self.assertFalse(Path(stored["dir"]).exists())
            self.assertEqual(usage.logs()["compilations"], [])


if __name__ == "__main__":
    unittest.main()
