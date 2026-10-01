"""Run one ffmpeg command and raise if it fails."""

from pathlib import Path

from app.errors import ConfigurationError
from app.jobs.runner import runner


class FfmpegError(Exception):
    """ffmpeg ran and reported a failure. The message is the tail of its output."""


def _run(command: list[str]) -> None:
    try:
        result = runner.run(command)
    except FileNotFoundError as exc:
        program = Path(command[0]).name if command else "ffmpeg"
        raise ConfigurationError(
            f"{program} was not found. Install ffmpeg and make sure it is on PATH."
        ) from exc
    if result.returncode != 0:
        detail = (result.stderr or result.stdout or "ffmpeg failed").strip()
        raise FfmpegError(detail[-800:])
