"""One page of videos from a channel tab."""

from typing import Any

import yt_dlp

from app.errors import ConfigurationError, terminal_message
from app.records import ListedVideo
from app.youtube.cookies import _with_cookies, private_cookies
from app.youtube.failures import YTDLP_ERRORS
from app.youtube.urls import ChannelError, normalize_channel_url


def list_channel_videos(url: str, limit: int, offset: int = 0) -> tuple[list[ListedVideo], bool]:
    """Return one page of channel videos and whether a later page exists.

    ``offset`` is how many playlist items to skip. Each call reads only that
    window, so a long channel can be scrolled through a page at a time.
    """
    if limit < 1:
        raise ChannelError("Limit must be at least 1")
    if offset < 0:
        raise ChannelError("Offset must be zero or greater")

    try:
        channel_url = normalize_channel_url(url)
        options = _with_cookies(
            {
                "extract_flat": "in_playlist",
                "quiet": True,
                "no_warnings": True,
                "skip_download": True,
                "playlist_items": f"{offset + 1}:{offset + limit}",
                "ignoreerrors": True,
            }
        )
        with private_cookies(options) as run_options, yt_dlp.YoutubeDL(run_options) as ydl:
            info = ydl.extract_info(channel_url, download=False)
    except ChannelError:
        raise
    except ConfigurationError as exc:
        raise ChannelError(str(exc)) from exc
    except YTDLP_ERRORS as exc:
        raise ChannelError(f"Could not read that channel: {exc}") from exc
    except OSError as exc:
        raise ChannelError(terminal_message(exc)) from exc

    if not info:
        if offset > 0:
            return [], False
        raise ChannelError("Could not read that channel")

    raw_entries = [entry for entry in (info.get("entries") or []) if entry]
    has_more = len(raw_entries) >= limit
    channel_name = info.get("channel") or info.get("uploader") or info.get("title")
    videos: list[ListedVideo] = []
    for entry in raw_entries:
        if not entry:
            continue
        video_id = entry.get("id")
        if not isinstance(video_id, str) or len(video_id) != 11:
            continue
        if entry.get("_type") not in (None, "url", "video"):
            continue
        title = entry.get("title") or "Untitled"
        thumbnail = _thumbnail(entry, video_id)
        duration = entry.get("duration")
        duration_seconds = int(duration) if isinstance(duration, (int, float)) else None
        views = entry.get("view_count")
        view_count = int(views) if isinstance(views, (int, float)) else None
        channel = entry.get("channel") or entry.get("uploader") or channel_name
        watch_url = entry.get("url") or ""
        if not watch_url.startswith("http"):
            watch_url = f"https://www.youtube.com/watch?v={video_id}"
        videos.append(
            {
                "video_id": video_id,
                "title": title,
                "thumbnail": thumbnail,
                "duration_seconds": duration_seconds,
                "url": watch_url,
                "channel": channel if isinstance(channel, str) else None,
                "view_count": view_count,
            }
        )
        if len(videos) >= limit:
            break

    if not videos:
        if offset > 0:
            return [], False
        raise ChannelError("No videos found for that channel")
    return videos, has_more


def _thumbnail(entry: dict[str, Any], video_id: str) -> str | None:
    thumbs = entry.get("thumbnails") or []
    if thumbs and isinstance(thumbs[-1], dict):
        url = thumbs[-1].get("url")
        if isinstance(url, str) and url:
            return url
    if len(video_id) == 11:
        return f"https://i.ytimg.com/vi/{video_id}/hqdefault.jpg"
    return None
