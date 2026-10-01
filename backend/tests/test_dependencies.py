"""Keep the install files aligned with pyproject.toml."""

import tomllib
import unittest
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]


def _listed_requirements(path: Path) -> list[str]:
    items: list[str] = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.split("#", 1)[0].strip()
        if not line or line.startswith("-"):
            continue
        items.append(line)
    return items


class DependencyManifestTests(unittest.TestCase):
    def test_runtime_requirements_match_pyproject(self) -> None:
        project = tomllib.loads((BACKEND / "pyproject.toml").read_text(encoding="utf-8"))
        declared = project["project"]["dependencies"]
        installed = _listed_requirements(BACKEND / "requirements.txt")
        self.assertEqual(installed, declared)

    def test_dev_requirements_match_pyproject(self) -> None:
        project = tomllib.loads((BACKEND / "pyproject.toml").read_text(encoding="utf-8"))
        declared = project["project"]["optional-dependencies"]["dev"]
        installed = _listed_requirements(BACKEND / "requirements-dev.txt")
        self.assertEqual(installed, declared)

    def test_desktop_requirements_match_pyproject(self) -> None:
        project = tomllib.loads((BACKEND / "pyproject.toml").read_text(encoding="utf-8"))
        declared = project["project"]["optional-dependencies"]["desktop"]
        desktop = BACKEND.parent / "packaging" / "requirements-desktop.txt"
        installed = _listed_requirements(desktop)
        self.assertEqual(installed, declared)
