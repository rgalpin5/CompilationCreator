"""The export routes over HTTP: status codes, response bodies and the file route."""

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from app.config import settings
from app.jobs.store import JobStore
from app.main import app
from app.routers import compilations
from app.usage.store import UsageStore
from tests.asgi import call

_BODY = json.dumps(
    {"clips": [{"video_id": "abcdefghijk", "start": "0:00", "end": "0:10"}]}
).encode()
_JSON = {"Content-Type": "application/json"}


class ExportRouteTests(unittest.TestCase):
    def setUp(self) -> None:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name)
        # What the lifespan does, pointed at a temporary folder.
        self.jobs = JobStore(root / "jobs")
        for name, value in (
            ("job_store", self.jobs),
            ("usage_store", UsageStore(root / "usage.json")),
        ):
            previous = getattr(app.state, name, None)
            setattr(app.state, name, value)
            self.addCleanup(setattr, app.state, name, previous)
        # The export itself is not run, so a started job stays queued.
        self.run_export = MagicMock()
        for patcher in (
            patch.object(compilations, "run_compilation", self.run_export),
            patch.object(settings, "password", None),
            patch.object(settings, "hosted", False),
        ):
            patcher.start()
            self.addCleanup(patcher.stop)

    def _start(self) -> dict[str, object]:
        status, _, body = call("/api/compilations", method="POST", headers=_JSON, body=_BODY)
        self.assertEqual(status, 202)
        job: dict[str, object] = json.loads(body)
        return job

    def test_start_returns_a_queued_job_without_server_paths(self) -> None:
        job = self._start()
        self.assertEqual(job["status"], "queued")
        self.assertNotIn("dir", job)
        self.assertNotIn("output_path", job)
        self.run_export.assert_called_once()

    def test_a_second_export_is_refused_while_one_runs(self) -> None:
        self._start()
        status, _, body = call("/api/compilations", method="POST", headers=_JSON, body=_BODY)
        self.assertEqual(status, 409)
        self.assertIn("still running", json.loads(body)["detail"])

    def test_invalid_timeline_and_unknown_job(self) -> None:
        empty = json.dumps({"clips": []}).encode()
        invalid, _, _ = call("/api/compilations", method="POST", headers=_JSON, body=empty)
        missing, _, body = call(f"/api/compilations/{'0' * 32}")
        self.assertEqual(invalid, 422)
        self.assertEqual(missing, 404)
        self.assertEqual(json.loads(body), {"detail": "Job not found"})

    def test_cancel_then_cancel_again(self) -> None:
        job = self._start()
        first, _, body = call(f"/api/compilations/{job['id']}/cancel", method="POST")
        again, _, _ = call(f"/api/compilations/{job['id']}/cancel", method="POST")
        self.assertEqual(first, 200)
        self.assertEqual(json.loads(body)["status"], "cancelled")
        self.assertEqual(again, 409)

    def test_file_route_serves_the_whole_video_or_a_range(self) -> None:
        job = self._start()
        job_id = str(job["id"])
        record = self.jobs.get(job_id)
        assert record is not None
        output = Path(record["dir"]) / "compilation.mp4"
        output.write_bytes(b"0123456789")
        self.jobs.update(job_id, status="ready", output_path=str(output))
        with patch.object(compilations.threading, "Timer") as timer:
            partial, part_headers, part_body = call(
                f"/api/compilations/{job_id}/file", headers={"Range": "bytes=2-5"}
            )
            still_ready = self.jobs.get(job_id)
            whole, headers, body = call(f"/api/compilations/{job_id}/file")
        self.assertEqual(partial, 206)
        self.assertEqual(part_body, b"2345")
        self.assertEqual(part_headers["content-range"], "bytes 2-5/10")
        assert still_ready is not None
        self.assertEqual(still_ready["status"], "ready")
        self.assertEqual(whole, 200)
        self.assertEqual(body, b"0123456789")
        self.assertEqual(headers["content-type"], "video/mp4")
        saved = self.jobs.get(job_id)
        assert saved is not None
        self.assertEqual(saved["status"], "saved")
        timer.assert_called_once()

    def test_file_route_refuses_a_job_that_is_not_ready(self) -> None:
        job = self._start()
        status, _, body = call(f"/api/compilations/{job['id']}/file")
        self.assertEqual(status, 404)
        self.assertEqual(json.loads(body)["detail"], "Compilation is not ready")


if __name__ == "__main__":
    unittest.main()
