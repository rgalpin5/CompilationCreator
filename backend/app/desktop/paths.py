"""Where the desktop app keeps its files."""

import os
import sys
from pathlib import Path

from app.errors import ConfigurationError, ensure_directory


def app_support_dir() -> Path:
    """Folder for jobs, the usage log, and the desktop log on this computer.

    The folder is created when it is missing. Permission problems and a path
    that is not a folder raise ``ConfigurationError``.
    """
    if sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support" / "CompCreator"
    elif sys.platform == "win32":
        root = os.environ.get("APPDATA") or str(Path.home() / "AppData" / "Roaming")
        base = Path(root) / "CompCreator"
    else:
        base = Path.home() / ".compcreator"
    ensure_directory(base, purpose="data folder")
    return base


def bundle_dirs() -> list[Path]:
    """Directories a frozen build should search for ffmpeg and the window files."""
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
    """Folder that contains the built ``index.html`` for the desktop window.

    A frozen app reads the copy PyInstaller extracted. A source checkout
    reads ``frontend/out``. A frozen app with no extracted files raises
    ``ConfigurationError``.
    """
    if getattr(sys, "frozen", False):
        # PyInstaller sets this attribute only inside a frozen executable.
        bundle = getattr(sys, "_MEIPASS", None)
        if not isinstance(bundle, str) or not bundle:
            raise ConfigurationError("The packaged app is missing its extracted files.")
        return Path(bundle) / "frontend"
    # backend/app/desktop/paths.py -> repository root is parents[3].
    return Path(__file__).resolve().parents[3] / "frontend" / "out"
