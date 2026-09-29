import contextvars
import os
import signal
import subprocess
import threading
import time

_job_id: contextvars.ContextVar[str | None] = contextvars.ContextVar("comp_job_id", default=None)


class JobCancelled(Exception):
    """The user stopped this export."""


class Runner:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._cancelled: set[str] = set()
        self._pids: dict[str, set[int]] = {}

    def bind(self, job_id: str) -> contextvars.Token[str | None]:
        return _job_id.set(job_id)

    def unbind(self, token: contextvars.Token[str | None]) -> None:
        _job_id.reset(token)

    def cancel(self, job_id: str) -> None:
        with self._lock:
            self._cancelled.add(job_id)
            pids = list(self._pids.get(job_id, ()))
        for pid in pids:
            _kill_group(pid)

    def kill(self, job_id: str) -> None:
        with self._lock:
            pids = list(self._pids.get(job_id, ()))
        for pid in pids:
            _kill_group(pid)

    def is_cancelled(self, job_id: str | None = None) -> bool:
        current = _job_id.get() if job_id is None else job_id
        if not current:
            return False
        with self._lock:
            return current in self._cancelled

    def checkpoint(self) -> None:
        if self.is_cancelled():
            raise JobCancelled()

    def run(self, command: list[str]) -> subprocess.CompletedProcess[str]:
        self.checkpoint()
        job_id = _job_id.get()
        proc = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            start_new_session=True,
        )
        if job_id:
            with self._lock:
                if job_id in self._cancelled:
                    pids_to_kill = [proc.pid]
                else:
                    self._pids.setdefault(job_id, set()).add(proc.pid)
                    pids_to_kill = []
            for pid in pids_to_kill:
                _kill_group(pid)
        try:
            stdout, stderr = proc.communicate()
        finally:
            if job_id:
                with self._lock:
                    self._pids.get(job_id, set()).discard(proc.pid)
        if job_id and self.is_cancelled(job_id):
            raise JobCancelled()
        return subprocess.CompletedProcess(command, proc.returncode or 0, stdout, stderr)


def _kill_group(pid: int) -> None:
    try:
        os.killpg(pid, signal.SIGTERM)
    except ProcessLookupError:
        return
    except PermissionError:
        try:
            os.kill(pid, signal.SIGTERM)
        except ProcessLookupError:
            return
    deadline = time.time() + 1
    while time.time() < deadline:
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            return
        time.sleep(0.05)
    try:
        os.killpg(pid, signal.SIGKILL)
    except ProcessLookupError:
        return


runner = Runner()
