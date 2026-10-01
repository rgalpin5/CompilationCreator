import asyncio
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi import HTTPException
from starlette.requests import Request
from starlette.types import Message

from app.delivery import deliver_compilation, resolve_directory, safe_filename
from app.jobs.store import JobStore
from app.models import DownloadRequest
from app.records import JobRecord
from app.routers import compilations


def _ready_job(root: Path, payload: bytes = b"final-video") -> tuple[JobStore, JobRecord, Path]:
    jobs = JobStore(root / "jobs")
    job = jobs.create()
    job_dir = Path(job["dir"])
    (job_dir / "raw_001.mp4").write_bytes(b"raw")
    (job_dir / "part_001.mp4").write_bytes(b"part")
    (job_dir / "norm_001.mp4").write_bytes(b"norm")
    (job_dir / "compilation.mp4").write_bytes(payload)
    (job_dir / "concat.txt").write_text("file 'part_001.mp4'\n", encoding="utf-8")
    source = job_dir / "compilation.mp4"
    jobs.update(
        job["id"],
        status="ready",
        output_path=str(source),
        filename="29 Sep, 15:36.mp4",
    )
    saved = jobs.get(job["id"])
    if saved is None:
        raise AssertionError("ready job was not stored")
    return jobs, saved, job_dir


class DeliveryTests(unittest.TestCase):
    def test_filename_replaces_characters_windows_rejects(self) -> None:
        self.assertEqual(safe_filename("29 Sep, 15:36.mp4"), "29 Sep, 15-36.mp4")
        self.assertEqual(safe_filename(None), "compilation.mp4")

    def test_blank_directory_is_downloads(self) -> None:
        path = resolve_directory("  ")
        self.assertEqual(path, (Path.home() / "Downloads").resolve())

    def test_missing_directory_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            missing = Path(tmp) / "nope"
            with self.assertRaises(ValueError):
                resolve_directory(str(missing))

    def test_relative_directory_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            resolve_directory("Downloads")

    def test_save_copies_the_video_and_deletes_working_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _jobs, job, job_dir = _ready_job(root)
            dest = root / "Downloads"
            dest.mkdir()
            saved = deliver_compilation(
                job_dir / "compilation.mp4", job["dir"], dest, job["filename"]
            )
            self.assertEqual(saved.name, "29 Sep, 15-36.mp4")
            self.assertEqual(saved.read_bytes(), b"final-video")
            self.assertFalse(job_dir.exists())

    def test_existing_file_gets_a_new_name(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _jobs, job, job_dir = _ready_job(root, b"second")
            dest = root / "Downloads"
            dest.mkdir()
            (dest / "29 Sep, 15-36.mp4").write_bytes(b"already-there")
            saved = deliver_compilation(
                job_dir / "compilation.mp4", job["dir"], dest, job["filename"]
            )
            self.assertEqual(saved.name, "29 Sep, 15-36 2.mp4")
            self.assertEqual(saved.read_bytes(), b"second")
            self.assertEqual((dest / "29 Sep, 15-36.mp4").read_bytes(), b"already-there")
            self.assertFalse(job_dir.exists())

    def test_folder_inside_the_job_is_rejected_and_files_stay(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _jobs, job, job_dir = _ready_job(root)
            with self.assertRaises(ValueError):
                deliver_compilation(
                    job_dir / "compilation.mp4", job["dir"], job_dir, job["filename"]
                )
            self.assertTrue((job_dir / "raw_001.mp4").is_file())
            self.assertTrue((job_dir / "compilation.mp4").is_file())

    def test_download_route_saves_and_clears_the_job(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            jobs, job, job_dir = _ready_job(root)
            dest = root / "out"
            dest.mkdir()
            result = compilations.download_compilation(
                job["id"],
                DownloadRequest(directory=str(dest)),
                jobs,
            )
            self.assertEqual(result.status, "saved")
            self.assertFalse(job_dir.exists())
            self.assertTrue(Path(result.saved_path or "").is_file())
            self.assertIsNone(result.download_url)
            with self.assertRaises(HTTPException) as caught:
                compilations.download_compilation(
                    job["id"],
                    DownloadRequest(directory=str(dest)),
                    jobs,
                )
            self.assertEqual(caught.exception.status_code, 409)

    def test_download_route_leaves_files_when_the_folder_is_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            jobs, job, job_dir = _ready_job(root)
            with self.assertRaises(HTTPException) as caught:
                compilations.download_compilation(
                    job["id"],
                    DownloadRequest(directory=str(root / "missing")),
                    jobs,
                )
            self.assertEqual(caught.exception.status_code, 400)
            self.assertTrue((job_dir / "part_001.mp4").is_file())
            self.assertTrue((job_dir / "compilation.mp4").is_file())
            stored = jobs.get(job["id"])
            self.assertIsNotNone(stored)
            assert stored is not None
            self.assertEqual(stored["status"], "ready")

    def test_save_succeeds_when_working_files_cannot_be_removed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            jobs, job, job_dir = _ready_job(root)
            dest = root / "out"
            dest.mkdir()
            with (
                patch("app.delivery.shutil.rmtree", side_effect=PermissionError("in use")),
                self.assertLogs("compcreator.delivery", level="WARNING"),
            ):
                result = compilations.download_compilation(
                    job["id"],
                    DownloadRequest(directory=str(dest)),
                    jobs,
                )
            self.assertEqual(result.status, "saved")
            self.assertEqual(Path(result.saved_path or "").read_bytes(), b"final-video")
            self.assertEqual(len(list(dest.iterdir())), 1)
            self.assertTrue(job_dir.is_dir())

    def test_hosted_server_rejects_a_custom_folder(self) -> None:
        with tempfile.TemporaryDirectory() as tmp, self.assertRaises(ValueError):
            resolve_directory(tmp, allow_custom=False)

    def test_hosted_server_accepts_its_default_folder(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            with patch("app.delivery.Path.home", return_value=home):
                blank = resolve_directory("", allow_custom=False)
                named = resolve_directory(str(home / "Downloads"), allow_custom=False)
            self.assertEqual(blank, (home / "Downloads").resolve())
            self.assertEqual(named, blank)


def _request(job_id: str, headers: dict[str, str] | None = None) -> Request:
    raw = [(k.lower().encode(), v.encode()) for k, v in (headers or {}).items()]
    path = f"/api/compilations/{job_id}/file"
    return Request({"type": "http", "method": "GET", "path": path, "headers": raw})


def _send_file(
    jobs: JobStore, job_id: str, headers: dict[str, str] | None = None, *, drop: bool = False
) -> tuple[bytes, dict[str, str]]:
    """Run the file route as an ASGI app. ``drop`` fails the send like a closed socket."""
    request = _request(job_id, headers)
    response = compilations.compilation_file(job_id, request, jobs)
    body = bytearray()
    sent_headers: dict[str, str] = {}

    async def receive() -> Message:
        await asyncio.sleep(3600)
        return {"type": "http.disconnect"}

    async def send(message: Message) -> None:
        if message["type"] == "http.response.start":
            sent_headers.update({k.decode(): v.decode() for k, v in message["headers"]})
        elif message["type"] == "http.response.body":
            if drop:
                raise OSError("connection reset")
            body.extend(message.get("body", b""))

    asyncio.run(response(request.scope, receive, send))
    return bytes(body), sent_headers


class BrowserDownloadTests(unittest.TestCase):
    def test_full_download_keeps_the_file_for_the_grace_period_then_clears_it(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            jobs, job, job_dir = _ready_job(Path(tmp))
            with patch("app.routers.compilations.threading.Timer") as timer:
                body, headers = _send_file(jobs, job["id"])
                # A second full download inside the grace period does not restart it.
                again, _ = _send_file(jobs, job["id"])
            self.assertEqual(body, b"final-video")
            self.assertEqual(again, b"final-video")
            self.assertEqual(headers["content-type"], "video/mp4")
            self.assertIn("attachment", headers["content-disposition"])
            self.assertTrue((job_dir / "compilation.mp4").is_file())
            stored = jobs.get(job["id"])
            assert stored is not None
            self.assertEqual(stored["status"], "saved")
            timer.assert_called_once()
            delay, expire, args = timer.call_args.args
            self.assertEqual(delay, compilations.BROWSER_DOWNLOAD_GRACE_SECONDS)

            expire(*args)
            self.assertFalse(job_dir.exists())
            with self.assertRaises(HTTPException) as caught:
                compilations.compilation_file(job["id"], _request(job["id"]), jobs)
            self.assertEqual(caught.exception.status_code, 404)
            self.assertIsNone(compilations.compilation_status(job["id"], jobs).file_url)

    def test_client_that_leaves_silently_can_still_download_again(self) -> None:
        # uvicorn drops writes after a disconnect instead of raising, so a
        # truncated download looks complete to the server.
        with tempfile.TemporaryDirectory() as tmp:
            jobs, job, job_dir = _ready_job(Path(tmp))
            with patch("app.routers.compilations.threading.Timer"):
                _send_file(jobs, job["id"])
                body, _ = _send_file(jobs, job["id"])
            self.assertEqual(body, b"final-video")
            self.assertTrue((job_dir / "compilation.mp4").is_file())

    def test_dropped_connection_keeps_the_job_ready(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            jobs, job, job_dir = _ready_job(Path(tmp))
            with self.assertRaises(OSError):
                _send_file(jobs, job["id"], drop=True)
            self.assertTrue((job_dir / "compilation.mp4").is_file())
            stored = jobs.get(job["id"])
            assert stored is not None
            self.assertEqual(stored["status"], "ready")

    def test_ranged_request_keeps_the_job_ready(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            jobs, job, job_dir = _ready_job(Path(tmp))
            body, _ = _send_file(jobs, job["id"], {"Range": "bytes=0-4"})
            self.assertEqual(body, b"final")
            self.assertTrue((job_dir / "compilation.mp4").is_file())
            stored = jobs.get(job["id"])
            assert stored is not None
            self.assertEqual(stored["status"], "ready")

    def test_unfinished_job_has_no_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            jobs = JobStore(Path(tmp) / "jobs")
            job = jobs.create()
            with self.assertRaises(HTTPException) as caught:
                compilations.compilation_file(job["id"], _request(job["id"]), jobs)
            self.assertEqual(caught.exception.status_code, 404)

    def test_hosted_status_offers_the_browser_link_and_refuses_a_server_save(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            jobs, job, job_dir = _ready_job(Path(tmp))
            with patch.object(compilations.settings, "hosted", True):
                status = compilations.compilation_status(job["id"], jobs)
                with self.assertRaises(HTTPException) as caught:
                    compilations.download_compilation(job["id"], None, jobs)
            self.assertEqual(status.file_url, f"/api/compilations/{job['id']}/file")
            self.assertIsNone(status.download_url)
            self.assertEqual(caught.exception.status_code, 409)
            self.assertTrue((job_dir / "compilation.mp4").is_file())

    def test_local_status_keeps_the_folder_save(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            jobs, job, _ = _ready_job(Path(tmp))
            with patch.object(compilations.settings, "hosted", False):
                status = compilations.compilation_status(job["id"], jobs)
            self.assertIsNone(status.file_url)
            self.assertEqual(status.download_url, f"/api/compilations/{job['id']}/download")


if __name__ == "__main__":
    unittest.main()
