import io
import logging
import tempfile
import unittest
from contextlib import redirect_stderr
from pathlib import Path
from unittest.mock import patch

from app.envfile import load_env_file
from app.errors import ConfigurationError, ensure_directory, terminal_message


class TerminalMessageTests(unittest.TestCase):
    def test_permission_names_the_path(self) -> None:
        exc = PermissionError(13, "Permission denied", "/tmp/CompCreator")
        self.assertEqual(terminal_message(exc), "Permission denied for /tmp/CompCreator.")

    def test_missing_file_names_the_path(self) -> None:
        exc = FileNotFoundError(2, "No such file or directory", "/tmp/missing.mp4")
        self.assertEqual(terminal_message(exc), "Could not find /tmp/missing.mp4.")

    def test_plain_missing_file_keeps_its_sentence(self) -> None:
        exc = FileNotFoundError("Compilation file is missing")
        self.assertEqual(terminal_message(exc), "Compilation file is missing")

    def test_configuration_uses_its_own_sentence(self) -> None:
        exc = ConfigurationError("YTDLP_COOKIES_FILE does not point at a cookies file.")
        self.assertEqual(terminal_message(exc), str(exc))

    def test_size_mismatch_keeps_the_oserror_sentence(self) -> None:
        exc = OSError("Saved file does not match the export")
        self.assertEqual(terminal_message(exc), "Saved file does not match the export")


class DirectoryTests(unittest.TestCase):
    def test_permission_denied_names_the_folder(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "jobs"
            denied = PermissionError(13, "Permission denied", str(target))
            with (
                patch.object(Path, "mkdir", side_effect=denied),
                self.assertRaises(ConfigurationError) as caught,
            ):
                ensure_directory(target, purpose="jobs folder")
        self.assertIn("Permission denied", str(caught.exception))
        self.assertIn(str(target), str(caught.exception))
        self.assertNotIn("Traceback", str(caught.exception))

    def test_file_in_the_way_is_not_a_folder(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "jobs"
            blocked = FileExistsError(17, "File exists", str(target))
            with (
                patch.object(Path, "mkdir", side_effect=blocked),
                self.assertRaises(ConfigurationError) as caught,
            ):
                ensure_directory(target, purpose="jobs folder")
        self.assertIn("not a folder", str(caught.exception))


class EnvFileFailureTests(unittest.TestCase):
    def test_unreadable_file_names_the_path(self) -> None:
        # chmod cannot make a file unreadable on Windows, so the denial is simulated.
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / ".env"
            path.write_text("JOBS_DIR=/tmp/jobs\n", encoding="utf-8")
            denied = PermissionError(13, "Permission denied", str(path))
            with (
                patch.object(Path, "read_text", side_effect=denied),
                self.assertRaises(ConfigurationError) as caught,
            ):
                load_env_file(path, {})
        message = str(caught.exception)
        self.assertIn("Permission denied", message)
        self.assertIn(str(path), message)

    def test_non_utf8_file_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / ".env"
            path.write_bytes(b"\xff\xfeJOBS_DIR")
            with self.assertRaises(ConfigurationError) as caught:
                load_env_file(path, {})
        self.assertIn("UTF-8", str(caught.exception))
        self.assertIn(str(path), str(caught.exception))


class DesktopStartupTests(unittest.TestCase):
    def test_denied_data_folder_prints_a_message_and_exits(self) -> None:
        from app import desktop

        denied = PermissionError(13, "Permission denied", "/tmp/CompCreator")
        stderr = io.StringIO()
        with (
            patch.object(desktop, "prepare_environment", side_effect=denied),
            redirect_stderr(stderr),
            self.assertRaises(SystemExit) as caught,
        ):
            desktop.main()
        text = stderr.getvalue()
        self.assertEqual(caught.exception.code, 1)
        self.assertNotIn("Traceback", text)
        self.assertIn("Permission denied for /tmp/CompCreator.", text)
        self.assertTrue(text.startswith("CompCreator: "))

    def test_missing_window_files_do_not_print_a_traceback(self) -> None:
        from app import desktop

        stderr = io.StringIO()
        root = logging.getLogger()
        before = list(root.handlers)
        with tempfile.TemporaryDirectory() as tmp:
            log_path = Path(tmp) / "desktop.log"
            failure = ConfigurationError(
                "The app window files were not found at /tmp/out. Run packaging/build.py first."
            )
            try:
                with (
                    patch.object(desktop, "prepare_environment", return_value=log_path),
                    patch.object(desktop, "_run", side_effect=failure),
                    redirect_stderr(stderr),
                    self.assertRaises(SystemExit) as caught,
                ):
                    desktop.main()
            finally:
                for handler in list(root.handlers):
                    if handler not in before:
                        handler.close()
                        root.removeHandler(handler)
        text = stderr.getvalue()
        self.assertEqual(caught.exception.code, 1)
        self.assertNotIn("Traceback", text)
        self.assertIn("app window files", text)
        if log_path.is_file():
            self.assertIn("app window files", log_path.read_text(encoding="utf-8"))


class UsageLogFailureTests(unittest.TestCase):
    def test_invalid_json_names_the_file(self) -> None:
        from app.usage.store import UsageStore

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "usage.json"
            path.write_text("{", encoding="utf-8")
            with self.assertRaises(ConfigurationError) as caught:
                UsageStore(path)
            message = str(caught.exception)
            self.assertIn("not valid JSON", message)
            self.assertIn(str(path), message)
            self.assertEqual(path.read_text(encoding="utf-8"), "{")
