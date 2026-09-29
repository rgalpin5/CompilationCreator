"""Open CompCreator in a desktop window and serve the API beside it.

The window loads this process, not a browser tab. Each install keeps its own
job files and, unless a cookie file is configured, reads YouTube cookies from
a browser on that computer.
"""

from __future__ import annotations

import logging
import os
import socket
import sys
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path

import uvicorn
from fastapi.staticfiles import StaticFiles

log = logging.getLogger("compcreator.desktop")


def app_support_dir() -> Path:
    if sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support" / "CompCreator"
    elif sys.platform == "win32":
        root = os.environ.get("APPDATA") or str(Path.home() / "AppData" / "Roaming")
        base = Path(root) / "CompCreator"
    else:
        base = Path.home() / ".compcreator"
    base.mkdir(parents=True, exist_ok=True)
    return base


def bundle_dirs() -> list[Path]:
    dirs: list[Path] = []
    if getattr(sys, "frozen", False):
        exe_dir = Path(sys.executable).resolve().parent
        dirs.append(exe_dir)
        meipass = getattr(sys, "_MEIPASS", None)
        if meipass:
            dirs.append(Path(meipass))
        contents = exe_dir.parent
        for name in ("Frameworks", "Resources"):
            sibling = contents / name
            if sibling.is_dir():
                dirs.append(sibling)
    return dirs


def static_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(getattr(sys, "_MEIPASS")) / "frontend"
    return Path(__file__).resolve().parents[2] / "frontend" / "out"


def detect_browser() -> str | None:
    """A browser on this machine that yt-dlp knows how to read cookies from."""
    if sys.platform == "darwin":
        candidates = [
            ("chrome", Path("/Applications/Google Chrome.app")),
            ("brave", Path("/Applications/Brave Browser.app")),
            ("edge", Path("/Applications/Microsoft Edge.app")),
            ("firefox", Path("/Applications/Firefox.app")),
            ("safari", Path("/Applications/Safari.app")),
        ]
    elif sys.platform == "win32":
        local = Path(os.environ.get("LOCALAPPDATA", ""))
        program = Path(os.environ.get("PROGRAMFILES", r"C:\Program Files"))
        program_x86 = Path(os.environ.get("PROGRAMFILES(X86)", r"C:\Program Files (x86)"))
        candidates = [
            ("chrome", local / "Google" / "Chrome" / "Application" / "chrome.exe"),
            ("chrome", program / "Google" / "Chrome" / "Application" / "chrome.exe"),
            ("edge", program_x86 / "Microsoft" / "Edge" / "Application" / "msedge.exe"),
            ("edge", program / "Microsoft" / "Edge" / "Application" / "msedge.exe"),
            ("brave", local / "BraveSoftware" / "Brave-Browser" / "Application" / "brave.exe"),
            ("firefox", program / "Mozilla Firefox" / "firefox.exe"),
        ]
    else:
        return None
    for name, path in candidates:
        if path.exists():
            return name
    return None


def prepare_environment() -> Path:
    """Point jobs, ffmpeg, and YouTube cookies at this computer. Returns the log path."""
    support = app_support_dir()
    os.environ.setdefault("COMPCREATOR_DESKTOP", "1")
    os.environ.setdefault("JOBS_DIR", str(support / "jobs"))
    extra = os.pathsep.join(str(path) for path in bundle_dirs())
    if extra:
        os.environ["PATH"] = extra + os.pathsep + os.environ.get("PATH", "")
    if not os.environ.get("YTDLP_COOKIES") and not os.environ.get("YTDLP_COOKIES_FILE"):
        os.environ.setdefault("YTDLP_COOKIES_BROWSER", detect_browser() or "none")
    return support / "desktop.log"


def mount_ui(application, directory: Path) -> None:
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
    raise RuntimeError(last_error)


def main() -> None:
    log_path = prepare_environment()
    logging.basicConfig(
        filename=log_path,
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )
    try:
        _run()
    except Exception:
        log.exception("CompCreator failed to start")
        raise


def _run() -> None:
    ui = static_dir()
    if not (ui / "index.html").is_file():
        raise SystemExit(f"UI build not found at {ui}. Run packaging/build.py first.")

    from app.main import app

    mount_ui(app, ui)
    port = _free_port()
    config = uvicorn.Config(app, host="127.0.0.1", port=port, log_level="info")
    server = uvicorn.Server(config)
    server.install_signal_handlers = lambda: None  # type: ignore[method-assign]
    thread = threading.Thread(target=server.run, name="compcreator-api", daemon=True)
    thread.start()
    url = f"http://127.0.0.1:{port}/"
    log.info("serving %s", url)
    _wait_until_ready(url + "health")

    import webview

    webview.create_window("CompCreator", url, width=1280, height=840, min_size=(900, 640))
    webview.start()
    server.should_exit = True
    thread.join(timeout=5)
