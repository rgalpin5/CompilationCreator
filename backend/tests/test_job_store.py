import os
import tempfile
import time
import unittest
import uuid
from pathlib import Path
from unittest.mock import patch

from app.jobs.store import STALE_AFTER_SECONDS, JobStore

_DAY = STALE_AFTER_SECONDS


def _age(folder: Path, seconds: float) -> None:
    """Backdate ``folder`` and everything directly inside it."""
    stamp = time.time() - seconds
    for path in [folder, *folder.iterdir()]:
        os.utime(path, (stamp, stamp))


def _leftover(root: Path, age: float, name: str | None = None) -> Path:
    folder = root / (name or uuid.uuid4().hex)
    folder.mkdir(parents=True)
    (folder / "raw_001.mp4").write_bytes(b"raw")
    _age(folder, age)
    return folder


class SweepTests(unittest.TestCase):
    def test_startup_removes_old_leftover_folders_only(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "jobs"
            old = _leftover(root, _DAY + 60)
            recent = _leftover(root, 60)
            JobStore(root)
            self.assertFalse(old.exists())
            self.assertTrue(recent.is_dir())

    def test_a_recent_file_keeps_an_old_folder(self) -> None:
        # A long ffmpeg run writes one file without touching the folder itself.
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "jobs"
            folder = _leftover(root, _DAY + 60)
            os.utime(folder / "raw_001.mp4")
            JobStore(root)
            self.assertTrue(folder.is_dir())

    def test_only_job_folders_are_ever_deleted(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "jobs"
            other = _leftover(root, _DAY * 30, name="Photos")
            short = _leftover(root, _DAY * 30, name="abc123")
            stray = root / ("f" * 32)
            stray.write_bytes(b"a file, not a job folder")
            os.utime(stray, (0, 0))
            JobStore(root)
            self.assertTrue(other.is_dir())
            self.assertTrue(short.is_dir())
            self.assertTrue(stray.is_file())

    def test_finished_jobs_expire_but_running_jobs_never_do(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            jobs = JobStore(Path(tmp) / "jobs")
            ready = jobs.create()
            running = jobs.create()
            fresh = jobs.create()
            jobs.update(ready["id"], status="ready", output_path="x.mp4")
            jobs.update(running["id"], status="downloading")
            later = time.time() + _DAY + 60
            jobs.update(fresh["id"], status="failed")
            with patch("app.jobs.store.time.time", return_value=later - 30):
                jobs.update(fresh["id"], progress="Failed")

            jobs.sweep(now=later)

            self.assertIsNone(jobs.get(ready["id"]))
            self.assertFalse(Path(ready["dir"]).exists())
            self.assertIsNotNone(jobs.get(running["id"]))
            self.assertTrue(Path(running["dir"]).is_dir())
            self.assertIsNotNone(jobs.get(fresh["id"]))
            self.assertTrue(Path(fresh["dir"]).is_dir())

    def test_creating_a_job_sweeps_first(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "jobs"
            jobs = JobStore(root)
            old = _leftover(root, _DAY + 60)
            jobs.create()
            self.assertFalse(old.exists())

    def test_a_folder_that_cannot_be_removed_is_logged_and_retried(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "jobs"
            jobs = JobStore(root)
            old = _leftover(root, _DAY + 60)
            with (
                patch("app.jobs.store.shutil.rmtree", side_effect=PermissionError("in use")),
                self.assertLogs("compcreator.jobs", level="WARNING"),
            ):
                self.assertEqual(jobs.sweep(), 0)
            self.assertTrue(old.is_dir())
            self.assertEqual(jobs.sweep(), 1)
            self.assertFalse(old.exists())


if __name__ == "__main__":
    unittest.main()
