import unittest
from pathlib import Path

from prereqs import (
    dev_command_hint,
    ffmpeg_install_hint,
    node_is_supported,
    node_major,
    python_is_supported,
    venv_python,
)


class PrereqTests(unittest.TestCase):
    def test_python_floor_is_3_12(self) -> None:
        self.assertFalse(python_is_supported((3, 11, 9)))
        self.assertTrue(python_is_supported((3, 12, 0)))
        self.assertTrue(python_is_supported((3, 13, 1)))

    def test_node_version_parsing(self) -> None:
        self.assertEqual(node_major("v22.14.0"), 22)
        self.assertTrue(node_is_supported("v20.0.0"))
        self.assertFalse(node_is_supported("v18.20.0"))
        with self.assertRaises(ValueError):
            node_major("nightly")

    def test_venv_interpreter_paths(self) -> None:
        venv = Path("/work/backend/.venv")
        self.assertEqual(venv_python(venv, "darwin"), venv / "bin" / "python")
        self.assertEqual(venv_python(venv, "linux"), venv / "bin" / "python")
        self.assertEqual(
            venv_python(venv, "win32"),
            venv / "Scripts" / "python.exe",
        )

    def test_platform_hints(self) -> None:
        self.assertEqual(dev_command_hint("win32"), "setup.bat dev")
        self.assertEqual(dev_command_hint("darwin"), "./setup.sh dev")
        self.assertIn("brew install ffmpeg", ffmpeg_install_hint("darwin"))
        self.assertIn("winget install", ffmpeg_install_hint("win32"))
        self.assertIn("apt-get install ffmpeg", ffmpeg_install_hint("linux"))
