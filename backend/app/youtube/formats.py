"""yt-dlp format strings for a 1080p or 4K source."""

import yt_dlp

from app.errors import ConfigurationError, terminal_message
from app.youtube.cookies import _with_cookies, private_cookies
from app.youtube.failures import YTDLP_ERRORS


def max_video_height(video_id: str) -> int | None:
    """Highest video-stream height YouTube offers for this id. None if unknown."""
    url = f"https://www.youtube.com/watch?v={video_id}"
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
            info = ydl.extract_info(url, download=False)
    except ConfigurationError as exc:
        raise RuntimeError(str(exc)) from exc
    except YTDLP_ERRORS as exc:
        raise RuntimeError(f"Could not read video formats: {exc}") from exc
    except OSError as exc:
        raise RuntimeError(terminal_message(exc)) from exc
    if not info:
        return None
    heights: list[int] = []
    for fmt in info.get("formats") or []:
        height = fmt.get("height")
        vcodec = fmt.get("vcodec")
        if isinstance(height, int) and vcodec not in (None, "none"):
            heights.append(height)
    return max(heights) if heights else None


def _format_selector(output_4k: bool) -> str:
    if output_4k:
        # Prefer a real 4K source. If YouTube does not have one, take the
        # largest smaller size and let ffmpeg scale it to 3840x2160.
        return (
            "bv*[height<=2160][vcodec^=avc1]+ba[acodec^=mp4a]/"
            "bv*[height<=2160][vcodec^=avc1]+ba/"
            "bv*[height<=2160]+ba/"
            "b"
        )
    return (
        "bv*[height<=1080][vcodec^=avc1]+ba[acodec^=mp4a]/"
        "bv*[height<=1080]+ba/b[height<=1080]/b"
    )
