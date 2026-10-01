"""Local API process: environment, static files, and a free port."""

import logging
import os
import socket
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.desktop.browser import detect_browser
from app.desktop.paths import app_support_dir, bundle_dirs
from app.errors import ConfigurationError

log = logging.getLogger("compcreator.desktop")


def ensure_stdio() -> None:
    """Give a windowed build streams that uvicorn can configure.

    PyInstaller ``--windowed`` on Windows leaves ``sys.stdout`` and
    ``sys.stderr`` as ``None``. Uvicorn's default formatter calls
    ``isatty()`` on stdout while building the ``default`` formatter, and
    that exits the program before the window opens.
    """
    if sys.stdout is None:
        sys.stdout = open(os.devnull, "w", encoding="utf-8")  # noqa: SIM115 - process-lifetime stream
    if sys.stderr is None:
        sys.stderr = open(os.devnull, "w", encoding="utf-8")  # noqa: SIM115 - process-lifetime stream


def prepare_environment() -> Path:
    """Point jobs, ffmpeg, and YouTube cookies at this computer.

    Returns the desktop log path. Creating the data folder raises
    ``ConfigurationError`` when the folder cannot be created.
    """
    support = app_support_dir()
    os.environ.setdefault("COMPCREATOR_DESKTOP", "1")
    os.environ.setdefault("JOBS_DIR", str(support / "jobs"))
    extra = os.pathsep.join(str(path) for path in bundle_dirs())
    if extra:
        os.environ["PATH"] = extra + os.pathsep + os.environ.get("PATH", "")
    if not os.environ.get("YTDLP_COOKIES") and not os.environ.get("YTDLP_COOKIES_FILE"):
        os.environ.setdefault("YTDLP_COOKIES_BROWSER", detect_browser() or "none")
    return support / "desktop.log"


def mount_ui(application: FastAPI, directory: Path) -> None:
    """Serve the built window files from ``directory`` at the site root."""
    application.mount("/", StaticFiles(directory=str(directory), html=True), name="ui")


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _wait_until_ready(url: str, timeout: float = 30) -> None:
    deadline = time.time() + timeout
    last_error = "server did not start"
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=1) as response:
                if response.status == 200:
                    return
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            last_error = str(exc)
            time.sleep(0.1)
    log.error("health check failed: %s", last_error)
    raise ConfigurationError(
        "The local server did not start. Check that this computer allows "
        "CompCreator to open a local port, then try again."
    )
