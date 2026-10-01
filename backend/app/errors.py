"""Failures a person running CompCreator on their own computer can act on."""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import NoReturn


class ConfigurationError(RuntimeError):
    """A setting, cookie file, or required program is missing or unusable."""


def terminal_message(exc: BaseException) -> str:
    """One sentence for ``exc``, without a traceback or an errno prefix."""
    if isinstance(exc, ConfigurationError):
        return str(exc).strip() or "A setting is missing or invalid."
    if isinstance(exc, PermissionError):
        target = _filename(exc)
        if target:
            return f"Permission denied for {target}."
        return "Permission denied."
    if isinstance(exc, FileNotFoundError):
        target = _filename(exc)
        if target:
            return f"Could not find {target}."
        text = str(exc).strip()
        return text or "A required file is missing."
    if isinstance(exc, OSError):
        text = str(exc).strip()
        if text and not text.startswith("[Errno"):
            return text
        target = _filename(exc)
        detail = exc.strerror or "the operating system rejected the request"
        if target:
            return f"Could not access {target}: {detail}."
        return f"Could not access a local file: {detail}."
    text = str(exc).strip()
    return text or "CompCreator could not continue."


def ensure_directory(path: Path, *, purpose: str) -> None:
    """Create ``path``, or raise ``ConfigurationError`` when that is not possible."""
    try:
        path.mkdir(parents=True, exist_ok=True)
    except PermissionError as exc:
        raise ConfigurationError(f"Permission denied creating the {purpose} at {path}.") from exc
    except FileExistsError as exc:
        raise ConfigurationError(f"The {purpose} at {path} is not a folder.") from exc
    except OSError as exc:
        detail = exc.strerror or "the operating system rejected the request"
        raise ConfigurationError(f"Could not create the {purpose} at {path}: {detail}.") from exc


def stop_for_local_error(exc: BaseException) -> NoReturn:
    """Print one line and stop the process.

    Uvicorn and Starlette attach a traceback to any exception that leaves the
    startup hook. Leaving the process here keeps a bad folder, a denied
    permission, or a broken settings file to the sentence in ``exc``.
    """
    print(f"CompCreator: {terminal_message(exc)}", file=sys.stderr)
    sys.stderr.flush()
    os._exit(1)


def _filename(exc: OSError) -> str | None:
    filename = exc.filename
    if isinstance(filename, str) and filename:
        return filename
    if isinstance(filename, bytes) and filename:
        return filename.decode("utf-8", "replace")
    return None
