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
        # Chrome, Edge and Brave on Windows encrypt cookies with a key only the
        # browser itself can unlock (app-bound encryption), so yt-dlp fails with
        # "failed to load cookies". Firefox is the one browser it can read there,
        # and only once a profile exists.
        appdata = Path(os.environ.get("APPDATA", ""))
        candidates = [("firefox", appdata / "Mozilla" / "Firefox" / "Profiles")]
    else:
        return None
    for name, path in candidates:
        if path.exists():
            return name
    return None
