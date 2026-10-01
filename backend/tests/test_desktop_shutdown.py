import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch


class _Server:
    """Stand-in for uvicorn.Server that records when it is told to exit."""

    def __init__(self, events: list[str]) -> None:
        self._events = events
        self._should_exit = False

    def run(self) -> None:
        return

    @property
    def should_exit(self) -> bool:
        return self._should_exit

    @should_exit.setter
    def should_exit(self, value: bool) -> None:
        self._events.append("server.should_exit")
        self._should_exit = value


class DesktopShutdownTests(unittest.TestCase):
    def test_closing_the_window_cancels_exports_before_the_server_stops(self) -> None:
        import app.desktop as desktop

        events: list[str] = []
        server = _Server(events)
        webview = types.ModuleType("webview")
        webview.create_window = MagicMock()  # type: ignore[attr-defined]
        webview.start = lambda: events.append("webview.start")  # type: ignore[attr-defined]

        with tempfile.TemporaryDirectory() as folder:
            ui = Path(folder)
            (ui / "index.html").write_text("<html></html>", encoding="utf-8")
            with (
                patch.dict(sys.modules, {"webview": webview}),
                patch.object(desktop, "static_dir", return_value=ui),
                patch.object(desktop, "mount_ui"),
                patch.object(desktop, "_free_port", return_value=1),
                patch.object(desktop, "_wait_until_ready"),
                patch.object(desktop.uvicorn, "Server", return_value=server),
                patch.object(
                    desktop.runner,
                    "cancel_all",
                    side_effect=lambda: events.append("runner.cancel_all"),
                ),
            ):
                desktop._run()

        self.assertEqual(events, ["webview.start", "runner.cancel_all", "server.should_exit"])


if __name__ == "__main__":
    unittest.main()
