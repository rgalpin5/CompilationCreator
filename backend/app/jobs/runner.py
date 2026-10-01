"""Cancellation tokens and child-process groups for an export."""

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
    """Tracks the child processes of one export so cancel can stop them."""

    def __init__(self) -> None:
        """Start with no cancelled jobs and no live child processes."""
        self._lock = threading.Lock()
        self._cancelled: set[str] = set()
        self._pids: dict[str, set[int]] = {}

    def bind(self, job_id: str) -> contextvars.Token[str | None]:
        """Make ``job_id`` the export for the current context. Return the reset token."""
        return _job_id.set(job_id)

    def unbind(self, token: contextvars.Token[str | None]) -> None:
        """Restore the export context captured by ``bind``."""
        _job_id.reset(token)

    def cancel(self, job_id: str) -> None:
        """Mark ``job_id`` cancelled and stop every child it still owns."""
        with self._lock:
            self._cancelled.add(job_id)
            pids = list(self._pids.get(job_id, ()))
        for pid in pids:
            _kill_group(pid)

    def forget(self, job_id: str) -> None:
        """Drop the cancel flag and process list of a finished export."""
        with self._lock:
            self._cancelled.discard(job_id)
            self._pids.pop(job_id, None)

    def is_cancelled(self, job_id: str | None = None) -> bool:
        """Whether ``job_id``, or the bound export, has been cancelled."""
        current = _job_id.get() if job_id is None else job_id
        if not current:
            return False
        with self._lock:
            return current in self._cancelled

    def checkpoint(self) -> None:
        """Raise ``JobCancelled`` when the bound export has been cancelled."""
        if self.is_cancelled():
            raise JobCancelled()

    def run(self, command: list[str]) -> subprocess.CompletedProcess[str]:
        """Run ``command`` in its own process group and wait for it to finish.

        A cancellation that arrives while the process is running stops that
        process group and raises ``JobCancelled``.
        """
        self.checkpoint()
        job_id = _job_id.get()
        # The extra keywords differ by platform. _popen_group_kwargs is covered
        # by tests; the splat is not one of Popen's static overloads.
        proc = subprocess.Popen(  # type: ignore[call-overload]
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            **_popen_group_kwargs(),
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


def _popen_group_kwargs() -> dict[str, object]:
    if _windows():
        # start_new_session is Unix-only. A new process group lets taskkill
        # stop yt-dlp and the ffmpeg process it spawned.
        flags = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
        return {"creationflags": flags}
    return {"start_new_session": True}


def _windows() -> bool:
    # os.killpg is missing on Windows. Checking the attribute covers a Python
    # build that reports a non-"nt" name but still has no process groups.
    return os.name == "nt" or not hasattr(os, "killpg")


def _kill_group(pid: int) -> None:
    try:
        if _windows():
            _kill_windows_tree(pid)
        else:
            _kill_posix_group(pid)
    except (OSError, AttributeError, subprocess.SubprocessError):
        return


def _kill_windows_tree(pid: int) -> None:
    subprocess.run(
        ["taskkill", "/F", "/T", "/PID", str(pid)],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )


def _kill_posix_group(pid: int) -> None:
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
