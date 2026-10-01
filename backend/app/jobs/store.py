"""In-memory export jobs and the folder each one writes into."""

import threading
import uuid
from pathlib import Path
from typing import Unpack

from app.errors import ensure_directory
from app.records import JobRecord, JobUpdate


class JobStore:
    """Export jobs for one API process, each with its own folder under ``root``."""

    def __init__(self, root: Path) -> None:
        """Create ``root`` and keep jobs in memory until this process exits."""
        self.root = root
        ensure_directory(self.root, purpose="jobs folder")
        self._jobs: dict[str, JobRecord] = {}
        self._lock = threading.Lock()

    def create(self) -> JobRecord:
        """Reserve a new job id and an empty working folder."""
        job_id = uuid.uuid4().hex
        job_dir = self.root / job_id
        ensure_directory(job_dir, purpose="export folder")
        job: JobRecord = {
            "id": job_id,
            "status": "queued",
            "progress": "Queued",
            "error": None,
            "dir": str(job_dir),
            "output_path": None,
        }
        with self._lock:
            self._jobs[job_id] = job
        return job.copy()

    def update(self, job_id: str, **fields: Unpack[JobUpdate]) -> None:
        """Change ``job_id`` when it still exists and has not been cancelled.

        A cancelled job ignores later updates, except another cancellation.
        Unknown jobs are ignored so a late worker cannot recreate one.
        """
        with self._lock:
            job = self._jobs.get(job_id)
            if not job:
                return
            if job["status"] == "cancelled" and fields.get("status") != "cancelled":
                return
            if "status" in fields:
                job["status"] = fields["status"]
            if "progress" in fields:
                job["progress"] = fields["progress"]
            if "error" in fields:
                job["error"] = fields["error"]
            if "dir" in fields:
                job["dir"] = fields["dir"]
            if "output_path" in fields:
                job["output_path"] = fields["output_path"]
            if "filename" in fields:
                job["filename"] = fields["filename"]
            if "saved_path" in fields:
                job["saved_path"] = fields["saved_path"]

    def get(self, job_id: str) -> JobRecord | None:
        """A copy of ``job_id``, or ``None`` when this process has no such job."""
        with self._lock:
            job = self._jobs.get(job_id)
            return job.copy() if job else None
