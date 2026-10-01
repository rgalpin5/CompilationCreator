"""In-memory export jobs and the folder each one writes into."""

import logging
import re
import shutil
import threading
import time
import uuid
from pathlib import Path
from typing import Unpack

from app.errors import ensure_directory
from app.records import JobRecord, JobUpdate

log = logging.getLogger("compcreator.jobs")

# No export runs this long, so a folder untouched for a day is not in use,
# even by another process that shares the jobs folder.
STALE_AFTER_SECONDS = 24 * 60 * 60

_ACTIVE = frozenset({"queued", "downloading", "concatenating"})
# Only folders named like a job id are ever deleted, so a JOBS_DIR that points
# somewhere unexpected cannot lose anything else.
_JOB_FOLDER = re.compile(r"[0-9a-f]{32}")


class JobStore:
    """Export jobs for one API process, each with its own folder under ``root``."""

    def __init__(self, root: Path, *, stale_after: float = STALE_AFTER_SECONDS) -> None:
        """Create ``root``, clear stale job folders, and keep jobs in memory until exit."""
        self.root = root
        self.stale_after = stale_after
        ensure_directory(self.root, purpose="jobs folder")
        self._jobs: dict[str, JobRecord] = {}
        self._touched: dict[str, float] = {}
        self._lock = threading.Lock()
        self.sweep()

    def create(self) -> JobRecord:
        """Reserve a new job id and an empty working folder."""
        self.sweep()
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
            self._touched[job_id] = time.time()
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
            self._touched[job_id] = time.time()

    def get(self, job_id: str) -> JobRecord | None:
        """A copy of ``job_id``, or ``None`` when this process has no such job."""
        with self._lock:
            job = self._jobs.get(job_id)
            return job.copy() if job else None

    def sweep(self, now: float | None = None) -> int:
        """Delete finished jobs and leftover folders untouched for ``stale_after`` seconds.

        Running jobs are never removed. A leftover folder is one no job in this
        process owns, such as the work of a process that crashed or restarted.
        A folder that cannot be deleted is logged and tried again next sweep.
        Returns how many folders were deleted.
        """
        now = time.time() if now is None else now
        cutoff = now - self.stale_after
        with self._lock:
            expired = {
                job_id
                for job_id, job in self._jobs.items()
                if job["status"] not in _ACTIVE and self._touched.get(job_id, now) < cutoff
            }
            for job_id in expired:
                del self._jobs[job_id]
                self._touched.pop(job_id, None)
            owned = set(self._jobs)

        try:
            entries = list(self.root.iterdir())
        except OSError:
            log.warning("Could not list the jobs folder %s", self.root, exc_info=True)
            return 0
        removed = 0
        for entry in entries:
            name = entry.name
            if name in owned or not _JOB_FOLDER.fullmatch(name) or not entry.is_dir():
                continue
            if name not in expired and _last_modified(entry, now) >= cutoff:
                continue
            try:
                shutil.rmtree(entry)
            except OSError:
                log.warning("Could not remove stale job folder %s", entry, exc_info=True)
                continue
            removed += 1
        return removed


def _last_modified(folder: Path, now: float) -> float:
    """Newest modification time of ``folder`` and the files directly inside it.

    An unreadable folder counts as just modified so it is left alone.
    """
    try:
        newest = folder.stat().st_mtime
        for child in folder.iterdir():
            newest = max(newest, child.stat().st_mtime)
    except OSError:
        return now
    return newest
