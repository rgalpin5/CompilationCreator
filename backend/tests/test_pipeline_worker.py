"""An export frees the one-export slot only once its worker has returned."""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from app.compilation import pipeline
from app.jobs.runner import JobCancelled
from app.jobs.store import JobStore


class WorkerSlotTests(unittest.TestCase):
    def _run_with(self, failure: BaseException) -> tuple[JobStore, str]:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        jobs = JobStore(Path(tmp.name) / "jobs")
        job = jobs.create_if_idle()
        assert job is not None
        with patch.object(pipeline, "_download_all", side_effect=failure):
            pipeline.run_compilation(jobs, job["id"], [])
        return jobs, job["id"]

    def test_a_cancelled_export_frees_the_slot_when_it_returns(self) -> None:
        jobs, job_id = self._run_with(JobCancelled())
        job = jobs.get(job_id)
        assert job is not None
        self.assertEqual(job["status"], "cancelled")
        self.assertIsNotNone(jobs.create_if_idle())

    def test_a_failed_export_frees_the_slot(self) -> None:
        jobs, job_id = self._run_with(RuntimeError("boom"))
        job = jobs.get(job_id)
        assert job is not None
        self.assertEqual(job["status"], "failed")
        self.assertIsNotNone(jobs.create_if_idle())

    def test_an_export_cancelled_before_it_starts_does_no_work(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            jobs = JobStore(Path(tmp) / "jobs")
            job = jobs.create_if_idle()
            assert job is not None
            jobs.cancel_if_active(job["id"])
            with patch.object(pipeline, "_download_all") as download:
                pipeline.run_compilation(jobs, job["id"], [])
            download.assert_not_called()
            self.assertFalse(Path(job["dir"]).exists())
            self.assertFalse(pipeline.runner.is_cancelled(job["id"]))
            self.assertIsNotNone(jobs.create_if_idle())

    def test_a_cancel_that_beats_ready_removes_the_finished_file(self) -> None:
        # The cancel route marks the store before the runner, so the pipeline
        # can reach its last step with the store cancelled and the runner not.
        with tempfile.TemporaryDirectory() as tmp:
            jobs = JobStore(Path(tmp) / "jobs")
            job = jobs.create()
            job_dir = Path(job["dir"])
            output = job_dir / "compilation.mp4"
            output.write_bytes(b"video")
            jobs.cancel_if_active(job["id"])
            pipeline._finish(jobs, job["id"], [], output, job_dir, None)
            after = jobs.get(job["id"])
        assert after is not None
        self.assertEqual(after["status"], "cancelled")
        self.assertFalse(job_dir.exists())

    def test_a_job_missing_from_the_store_still_frees_its_slot(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            jobs = JobStore(Path(tmp) / "jobs")
            job = jobs.create_if_idle()
            assert job is not None
            with patch.object(jobs, "get", return_value=None):
                pipeline.run_compilation(jobs, job["id"], [])
            jobs.update(job["id"], status="ready")
            self.assertIsNotNone(jobs.create_if_idle())


if __name__ == "__main__":
    unittest.main()
