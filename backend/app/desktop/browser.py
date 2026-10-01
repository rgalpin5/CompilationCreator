"""Which installed browser yt-dlp should read cookies from."""

import os
import sys
from pathlib import Path


def detect_browser() -> str | None:
    """A browser on this machine that yt-dlp knows how to read cookies from."""
    # Declared up front: mypy only checks the branch for the platform it runs on.
    candidates: list[tuple[str, Path]]
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
