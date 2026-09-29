"""PyInstaller entry. Adds the backend to sys.path when running from source."""

import sys
from pathlib import Path

if not getattr(sys, "frozen", False):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app.desktop import main

if __name__ == "__main__":
    main()
