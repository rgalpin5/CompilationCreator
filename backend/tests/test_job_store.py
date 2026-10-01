import os
import tempfile
import time
import unittest
import uuid
from concurrent.futures import ThreadPoolExecutor
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


class CancelIfActiveTests(unittest.TestCase):
    def test_cancels_only_a_job_that_is_still_working(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            jobs = JobStore(Path(tmp) / "jobs")
            working = jobs.create()
            finished = jobs.create()
            jobs.update(finished["id"], status="ready", output_path="/tmp/out.mp4")
            self.assertEqual(jobs.cancel_if_active(working["id"]), "cancelled")
            self.assertEqual(jobs.cancel_if_active(finished["id"]), "not_running")
            self.assertEqual(jobs.cancel_if_active(uuid.uuid4().hex), "missing")
            cancelled = jobs.get(working["id"])
            ready = jobs.get(finished["id"])
        assert cancelled is not None and ready is not None
        self.assertEqual(cancelled["status"], "cancelled")
        self.assertIsNone(cancelled["output_path"])
        self.assertEqual(ready["status"], "ready")
        self.assertEqual(ready["output_path"], "/tmp/out.mp4")

    def test_a_ready_update_after_cancel_is_ignored(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            jobs = JobStore(Path(tmp) / "jobs")
            job = jobs.create()
            jobs.cancel_if_active(job["id"])
            jobs.update(job["id"], status="ready", output_path="/tmp/out.mp4")
            after = jobs.get(job["id"])
        assert after is not None
        self.assertEqual(after["status"], "cancelled")
        self.assertIsNone(after["output_path"])


class OneExportAtATimeTests(unittest.TestCase):
    def test_create_if_idle_waits_for_the_running_export(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            jobs = JobStore(Path(tmp) / "jobs")
            first = jobs.create_if_idle()
            assert first is not None
            self.assertIsNone(jobs.create_if_idle())
            jobs.update(first["id"], status="downloading")
            self.assertIsNone(jobs.create_if_idle())
            jobs.update(first["id"], status="ready")
            jobs.worker_stopped(first["id"])
            self.assertIsNotNone(jobs.create_if_idle())

    def test_a_cancelled_export_blocks_the_next_until_its_worker_stops(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            jobs = JobStore(Path(tmp) / "jobs")
            first = jobs.create_if_idle()
            assert first is not None
            jobs.update(first["id"], status="cancelled")
            self.assertIsNone(jobs.create_if_idle())
            jobs.worker_stopped(first["id"])
            self.assertIsNotNone(jobs.create_if_idle())

    def test_sweep_keeps_a_cancelled_job_whose_worker_is_still_running(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            jobs = JobStore(Path(tmp) / "jobs", stale_after=0)
            job = jobs.create_if_idle()
            assert job is not None
            jobs.update(job["id"], status="cancelled")
            jobs.sweep(now=time.time() + 10)
            self.assertIsNotNone(jobs.get(job["id"]))
            self.assertTrue(Path(job["dir"]).is_dir())
            jobs.worker_stopped(job["id"])
            jobs.sweep(now=time.time() + 10)
            self.assertIsNone(jobs.get(job["id"]))

    def test_only_one_of_many_simultaneous_requests_starts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            jobs = JobStore(Path(tmp) / "jobs")
            with ThreadPoolExecutor(max_workers=8) as pool:
                results = list(pool.map(lambda _: jobs.create_if_idle(), range(16)))
            self.assertEqual(sum(result is not None for result in results), 1)


if __name__ == "__main__":
    unittest.main()
