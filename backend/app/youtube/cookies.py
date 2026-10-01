"""YouTube cookie file, browser login, and the Deno path yt-dlp needs."""

import base64
import contextlib
import os
import shutil
import sys
import tempfile
import threading
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from app.errors import ConfigurationError

YtdlpOptions = dict[str, Any]

# YTDLP_COOKIES contents -> the private file written for them this process.
_env_cookie_files: dict[str, str] = {}
_env_cookie_lock = threading.Lock()


def _with_cookies(options: YtdlpOptions) -> YtdlpOptions:
    cookiefile = _cookiefile()
    if cookiefile:
        options["cookiefile"] = cookiefile
        return _with_challenge_solver(options)
    browser = _browser_name()
    if browser:
        options["cookiesfrombrowser"] = (browser,)
        return _with_challenge_solver(options)
    return options


def _with_challenge_solver(options: YtdlpOptions) -> YtdlpOptions:
    """Unlock formats when a YouTube login is sent with the request.

    Logged-in clients withhold media URLs until yt-dlp solves the n challenge.
    Deno is named by full path because a Mac app opened from Finder does not
    inherit Homebrew on PATH.
    """
    deno = _deno_path()
    if not deno:
        raise ConfigurationError(
            "YouTube login needs Deno 2.3 or newer installed so video formats can be unlocked."
        )
    options["js_runtimes"] = {"deno": {"path": deno}}
    options["remote_components"] = ["ejs:github"]
    return options


def _deno_path() -> str | None:
    override = os.environ.get("YTDLP_DENO", "").strip()
    if override:
        return override if _executable(override) else None
    found = shutil.which("deno")
    if found:
        return found
    name = "deno.exe" if sys.platform == "win32" else "deno"
    candidates = [Path.home() / ".deno" / "bin" / name]
    if sys.platform == "win32":
        local = os.environ.get("LOCALAPPDATA", "")
        if local:
            candidates.append(Path(local) / "deno" / name)
    else:
        candidates.extend(
            [
                Path("/opt/homebrew/bin") / name,
                Path("/usr/local/bin") / name,
            ]
        )
    for candidate in candidates:
        if _executable(candidate):
            return str(candidate)
    return None


def _executable(path: str | Path) -> bool:
    return os.access(path, os.X_OK) and not os.path.isdir(path)


def _browser_name() -> str | None:
    """Browser whose YouTube login yt-dlp should read, if one was selected.

    A cookie file wins over this. The desktop app sets the variable to the
    browser installed on that computer so each person uses their own account.
    """
    name = os.environ.get("YTDLP_COOKIES_BROWSER", "").strip().lower()
    if name in {"", "0", "none", "off"}:
        return None
    return name


def _cookiefile() -> str | None:
    """Netscape cookies for YouTube, if the operator supplied them.

    YTDLP_COOKIES_FILE is a path. YTDLP_COOKIES is the file contents, or the
    same contents encoded as base64. Nothing is read from a browser.
    """
    configured = os.environ.get("YTDLP_COOKIES_FILE", "").strip()
    if configured:
        path = Path(configured)
        if not path.is_file():
            raise ConfigurationError(
                f"YTDLP_COOKIES_FILE does not point at a cookies file ({path})."
            )
        return str(path)

    raw = os.environ.get("YTDLP_COOKIES", "").strip()
    if not raw:
        return None
    if "\\n" in raw and "\n" not in raw:
        raw = raw.replace("\\n", "\n")
    text = raw
    if "youtube.com" not in raw and not raw.startswith("#"):
        try:
            text = base64.b64decode(raw, validate=True).decode("utf-8")
        except (ValueError, UnicodeDecodeError):
            text = raw
    body = text if text.endswith("\n") else text + "\n"
    with _env_cookie_lock:
        cached = _env_cookie_files.get(body)
        if cached and Path(cached).is_file():
            return cached
        written = _write_private(body.encode("utf-8"), purpose="cookie file")
        _env_cookie_files[body] = written
        return written


@contextmanager
def private_cookies(options: YtdlpOptions) -> Iterator[YtdlpOptions]:
    """Give one yt-dlp run its own copy of the cookie file.

    yt-dlp rewrites its cookie file when it closes. Parallel downloads that
    shared one file could truncate it while another run was reading it.
    """
    source = options.get("cookiefile")
    if not source:
        yield options
        return
    try:
        data = Path(source).read_bytes()
    except OSError as exc:
        detail = exc.strerror or "the operating system rejected the request"
        raise ConfigurationError(f"Could not read the cookie file at {source}: {detail}.") from exc
    copy = _write_private(data, purpose="cookie copy")
    try:
        yield {**options, "cookiefile": copy}
    finally:
        with contextlib.suppress(OSError):
            os.unlink(copy)


def _write_private(data: bytes, *, purpose: str) -> str:
    """Write ``data`` to a new owner-only temp file and return its path."""
    try:
        # mkstemp picks an unpredictable name and creates the file as 0600.
        fd, path = tempfile.mkstemp(prefix="compcreator-cookies-", suffix=".txt")
        with os.fdopen(fd, "wb") as handle:
            handle.write(data)
    except PermissionError as exc:
        raise ConfigurationError(
            f"Permission denied writing the {purpose} in {tempfile.gettempdir()}."
        ) from exc
    except OSError as exc:
        detail = exc.strerror or "the operating system rejected the request"
        raise ConfigurationError(
            f"Could not write the {purpose} in {tempfile.gettempdir()}: {detail}."
        ) from exc
    return path
