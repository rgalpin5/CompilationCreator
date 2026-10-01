"""Open CompCreator in a desktop window and serve the API beside it.

The window loads this process, not a browser tab. Each install keeps its own
job files and, unless a cookie file is configured, reads YouTube cookies from
a browser on that computer.
"""

from __future__ import annotations

import logging
import sys
import threading
from typing import NoReturn

import uvicorn

from app.desktop.paths import static_dir
from app.desktop.server import (
    _free_port,
    _wait_until_ready,
    ensure_stdio,
    mount_ui,
    prepare_environment,
)
from app.errors import ConfigurationError, terminal_message
from app.jobs.runner import runner

log = logging.getLogger("compcreator.desktop")


def main() -> None:
    """Open the desktop window.

    A missing window build, a data folder that cannot be created, or any
    other local setup problem prints one line to the terminal and exits
    with status 1. The same sentence is written to the desktop log when
    that log could be opened.
    """
    ensure_stdio()
    try:
        log_path = prepare_environment()
        logging.basicConfig(
            filename=log_path,
            level=logging.INFO,
            format="%(asctime)s %(levelname)s %(message)s",
        )
        _run()
    except (ConfigurationError, OSError) as exc:
        message = terminal_message(exc)
        if logging.getLogger().handlers:
            log.error("%s", message)
        _fail(message)


def _fail(message: str) -> NoReturn:
    print(f"CompCreator: {message}", file=sys.stderr)
    raise SystemExit(1) from None


def _run() -> None:
    ui = static_dir()
    if not (ui / "index.html").is_file():
        raise ConfigurationError(
            f"The app window files were not found at {ui}. Run packaging/build.py first."
        )

    from app.main import app

    mount_ui(app, ui)
    port = _free_port()
    config = uvicorn.Config(app, host="127.0.0.1", port=port, log_level="info")
    server = uvicorn.Server(config)
    server.install_signal_handlers = lambda: None  # type: ignore[attr-defined]
    thread = threading.Thread(target=server.run, name="compcreator-api", daemon=True)
    thread.start()
    url = f"http://127.0.0.1:{port}/"
    log.info("serving %s", url)
    _wait_until_ready(url + "health")

    try:
        import webview
    except ImportError as exc:
        raise ConfigurationError(
            "The desktop window library is not installed. "
            "Install the desktop requirements and try again."
        ) from exc

    webview.create_window("CompCreator", url, width=1280, height=840, min_size=(900, 640))
    webview.start()
    # Export children run in their own process groups and would outlive the
    # window, so stop any running export before the server shuts down.
    runner.cancel_all()
    server.should_exit = True
    thread.join(timeout=5)
