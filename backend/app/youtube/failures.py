"""yt-dlp exceptions this process knows how to explain to a local user."""

from __future__ import annotations

import yt_dlp


def ytdlp_error_types() -> tuple[type[BaseException], ...]:
    """Return yt-dlp's error base class for this install.

    The library is untyped, so the class is checked at runtime instead of
    being imported as a name mypy would treat as ``Any``.
    """
    utils = getattr(yt_dlp, "utils", None)
    error_type = getattr(utils, "YoutubeDLError", None)
    if isinstance(error_type, type) and issubclass(error_type, BaseException):
        return (error_type,)
    return ()


YTDLP_ERRORS: tuple[type[BaseException], ...] = ytdlp_error_types()
