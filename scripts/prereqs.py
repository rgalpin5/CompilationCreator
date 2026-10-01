"""Checks and path helpers shared by the local setup command.

These functions stay free of installs and network access so unit tests can
cover the platform decisions without creating a virtualenv.
"""

from __future__ import annotations

import sys
from pathlib import Path

MIN_PYTHON = (3, 12)
MIN_NODE = 20


def python_is_supported(version: tuple[int, ...]) -> bool:
    """Return whether ``version`` satisfies the backend's Python requirement."""
    return version >= MIN_PYTHON


def node_major(raw: str) -> int:
    """Parse a ``node --version`` string such as ``v22.14.0``."""
    text = raw.strip().lstrip("v").split(".", 1)[0]
    if not text.isdigit():
        raise ValueError(f"Could not read the Node.js version from {raw!r}.")
    return int(text)


def node_is_supported(raw: str) -> bool:
    """Return whether ``raw`` is Node.js 20 or newer."""
    return node_major(raw) >= MIN_NODE


def venv_python(venv: Path, platform: str | None = None) -> Path:
    """Return the interpreter path inside a virtualenv for ``platform``."""
    system = sys.platform if platform is None else platform
    if system == "win32":
        return venv / "Scripts" / "python.exe"
    return venv / "bin" / "python"


def dev_command_hint(platform: str | None = None) -> str:
    """Return the command that starts the API and the UI on this OS."""
    system = sys.platform if platform is None else platform
    if system == "win32":
        return "setup.bat dev"
    return "./setup.sh dev"


def ffmpeg_install_hint(platform: str | None = None) -> str:
    """Return the install command for ffmpeg and ffprobe on ``platform``."""
    system = sys.platform if platform is None else platform
    if system == "darwin":
        return "Install both with: brew install ffmpeg"
    if system == "win32":
        return "Install both with: winget install Gyan.FFmpeg"
    return "Install both with your package manager, for example: sudo apt-get install ffmpeg"
