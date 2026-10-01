import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi import HTTPException

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


if __name__ == "__main__":
    unittest.main()
