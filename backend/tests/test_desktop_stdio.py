import sys
import unittest

import uvicorn


class WindowedStdioTests(unittest.TestCase):
    def test_existing_streams_stay_in_place(self) -> None:
        from app.desktop import ensure_stdio

        stdout, stderr = sys.stdout, sys.stderr
        ensure_stdio()
        self.assertIs(sys.stdout, stdout)
        self.assertIs(sys.stderr, stderr)

    def test_missing_console_can_configure_uvicorn(self) -> None:
        from app.desktop import ensure_stdio

        stdout, stderr = sys.stdout, sys.stderr
        sys.stdout = None
        sys.stderr = None
        try:
            ensure_stdio()
            self.assertIsNotNone(sys.stdout)
            self.assertIsNotNone(sys.stderr)
            assert sys.stdout is not None
            assert sys.stderr is not None
            self.assertFalse(sys.stdout.isatty())
            self.assertFalse(sys.stderr.isatty())
            uvicorn.Config(lambda: None, host="127.0.0.1", port=1, log_level="info")
        finally:
            sys.stdout = stdout
            sys.stderr = stderr
