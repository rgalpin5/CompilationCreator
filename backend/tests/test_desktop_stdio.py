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
            # Building the config sets up uvicorn's logging, which is the step
            # that used to exit a windowed build. Windows reports its null
            # device as a terminal, so isatty() is not checked here.
            uvicorn.Config(lambda: None, host="127.0.0.1", port=1, log_level="info")
        finally:
            for stream in (sys.stdout, sys.stderr):
                if stream is not None and stream not in (stdout, stderr):
                    stream.close()
            sys.stdout = stdout
            sys.stderr = stderr
