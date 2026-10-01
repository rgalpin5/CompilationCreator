"""Turn a pasted YouTube link into a channel videos-tab URL."""

from urllib.parse import ParseResult, urlparse, urlunparse

import yt_dlp

from app.errors import ConfigurationError, terminal_message
from app.youtube.cookies import _with_cookies, private_cookies
from app.youtube.failures import YTDLP_ERRORS

_YOUTUBE_HOSTS = {
    "youtube.com",
    "www.youtube.com",
    "m.youtube.com",
    "music.youtube.com",
}
_SHORT_HOSTS = {"youtu.be", "www.youtu.be"}
_VIDEO_KINDS = {"shorts", "live", "embed", "v"}
_TAB_SUFFIXES = ("/videos", "/streams", "/shorts", "/playlists", "/featured")


class ChannelError(Exception):
    """User-facing failure while reading a channel."""


def _is_video_id(value: str) -> bool:
    return len(value) == 11 and all(char.isalnum() or char in "-_" for char in value)


def _video_page_url(parsed: ParseResult) -> str | None:
    host = parsed.netloc.lower()
    parts = [part for part in parsed.path.split("/") if part]
    if host in _SHORT_HOSTS and parts and _is_video_id(parts[0]):
        return f"https://www.youtube.com/watch?v={parts[0]}"
    if host not in _YOUTUBE_HOSTS:
        return None
    if parsed.path.rstrip("/") == "/watch":
        return str(urlunparse(parsed._replace(params="", fragment="")))
    if len(parts) >= 2 and parts[0] in _VIDEO_KINDS and _is_video_id(parts[1]):
        return f"https://www.youtube.com/watch?v={parts[1]}"
    return None


def _uploader_channel_url(video_url: str) -> str:
    try:
        options = _with_cookies(
            {
                "quiet": True,
                "no_warnings": True,
                "skip_download": True,
                "noplaylist": True,
            }
        )
        with private_cookies(options) as run_options, yt_dlp.YoutubeDL(run_options) as ydl:
            info = ydl.extract_info(video_url, download=False)
    except ConfigurationError as exc:
        raise ChannelError(str(exc)) from exc
    except YTDLP_ERRORS as exc:
        raise ChannelError(f"Could not resolve that video to a channel: {exc}") from exc
    except OSError as exc:
        raise ChannelError(terminal_message(exc)) from exc
    channel = (info or {}).get("uploader_url") or (info or {}).get("channel_url")
    if not isinstance(channel, str) or not channel.startswith(("http://", "https://")):
        raise ChannelError("Could not resolve that video to a channel")
    return channel


def normalize_channel_url(url: str) -> str:
    """Return the videos-tab URL for a channel, handle, or single video link.

    A watch link or ``youtu.be`` link is resolved to that video's channel.
    Anything that is not a YouTube channel raises ``ChannelError``.
    """
    raw = url.strip()
    if raw.startswith("@"):
        raw = f"https://www.youtube.com/{raw}"
    if not raw.startswith(("http://", "https://")):
        raw = "https://" + raw

    parsed = urlparse(raw)
    video_url = _video_page_url(parsed)
    if video_url:
        channel = _uploader_channel_url(video_url)
        if _video_page_url(urlparse(channel)):
            raise ChannelError("Could not resolve that video to a channel")
        return normalize_channel_url(channel)

    host = parsed.netloc.lower()
    if host not in _YOUTUBE_HOSTS:
        raise ChannelError("Paste a YouTube channel URL")

    path = parsed.path.rstrip("/") or "/"
    if path.startswith("/playlist"):
        raise ChannelError("Paste a channel URL, not a playlist")

    if not any(path.endswith(suffix) for suffix in _TAB_SUFFIXES):
        path = path + "/videos"

    return urlunparse(parsed._replace(path=path, params="", query="", fragment=""))
