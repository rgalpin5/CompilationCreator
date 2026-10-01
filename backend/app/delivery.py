"""Move a finished compilation out of the job folder.

The export keeps raw clips, trimmed parts, and the joined file beside each
other until the user saves. Saving copies the joined file into Downloads, or
into a folder they name, and then deletes that job folder.
"""

from __future__ import annotations

import logging
import re
import shutil
import uuid
from pathlib import Path

log = logging.getLogger("compcreator.delivery")

_UNSAFE = re.compile(r'[<>:"/\\|?*\x00-\x1f]')


def default_download_dir() -> Path:
    """The Downloads folder in the current user's home directory."""
    return Path.home() / "Downloads"


def resolve_directory(raw: str | None, *, allow_custom: bool = True) -> Path:
    """A folder the finished video may be written into.

    With ``allow_custom`` false, only the default Downloads folder is accepted.
    """
    default = default_download_dir()
    if raw is None or not str(raw).strip() or Path(str(raw).strip()) == default:
        default.mkdir(parents=True, exist_ok=True)
        return default.resolve()
    if not allow_custom:
        raise ValueError("This server saves to its default folder only. Leave the folder blank.")
    path = Path(str(raw).strip()).expanduser()
    if not path.is_absolute():
        raise ValueError("Save folder must be a full path, such as /Users/you/Downloads")
    if not path.is_dir():
        raise ValueError("That folder does not exist")
    return path.resolve()


def safe_filename(name: str | None) -> str:
    """A single ``.mp4`` file name that Windows, macOS, and Linux will accept."""
    text = _UNSAFE.sub("-", (name or "").strip()).strip(" .")
    if not text:
        text = "compilation"
    if not text.lower().endswith(".mp4"):
        text = f"{text}.mp4"
    return text[:180]


def _unique_destination(directory: Path, filename: str) -> Path:
    candidate = directory / filename
    if not candidate.exists():
        return candidate
    stem = Path(filename).stem
    suffix = Path(filename).suffix or ".mp4"
    number = 2
    while True:
        candidate = directory / f"{stem} {number}{suffix}"
        if not candidate.exists():
            return candidate
        number += 1


def _is_inside(path: Path, parent: Path) -> bool:
    try:
        path.resolve().relative_to(parent.resolve())
    except ValueError:
        return False
    return True


def deliver_compilation(
    source: str | Path,
    job_dir: str | Path,
    directory: str | Path,
    filename: str | None,
) -> Path:
    """Copy the finished video, then delete the job folder.

    The job folder is removed only after the saved file matches the export.
    A job folder that cannot be removed is logged and left in place.
    """
    source = Path(source).resolve()
    job_dir = Path(job_dir).resolve()
    directory = Path(directory).resolve()
    if not source.is_file():
        raise FileNotFoundError("Compilation file is missing")
    if _is_inside(directory, job_dir):
        raise ValueError("Choose a folder outside the export's working files")

    target = _unique_destination(directory, safe_filename(filename))
    partial = directory / f".compcreator-{uuid.uuid4().hex}.partial"
    try:
        shutil.copy2(source, partial)
        if partial.stat().st_size != source.stat().st_size:
            raise OSError("Saved file does not match the export")
        partial.replace(target)
    except OSError:
        partial.unlink(missing_ok=True)
        raise
    try:
        shutil.rmtree(job_dir)
    except OSError:
        # The video is already saved. A file still held open (common on
        # Windows) must not turn that into an error and invite a second copy.
        log.warning("Could not remove working files at %s", job_dir, exc_info=True)
    return target
