import base64
import os
import sys
import tempfile
from pathlib import Path
from urllib.parse import urlparse, urlunparse

import yt_dlp

from app.services.runner import runner

_YOUTUBE_HOSTS = {
    "youtube.com",
    "www.youtube.com",
    "m.youtube.com",
    "music.youtube.com",
}
_TAB_SUFFIXES = ("/videos", "/streams", "/shorts", "/playlists", "/featured")


class ChannelError(Exception):
    """User-facing failure while reading a channel."""


def normalize_channel_url(url: str) -> str:
    raw = url.strip()
    if raw.startswith("@"):
        raw = f"https://www.youtube.com/{raw}"
    if not raw.startswith(("http://", "https://")):
        raw = "https://" + raw

    parsed = urlparse(raw)
    host = parsed.netloc.lower()
    if host not in _YOUTUBE_HOSTS:
        raise ChannelError("Paste a YouTube channel URL")

    path = parsed.path.rstrip("/") or "/"
    if path == "/watch" or path.startswith("/watch"):
        raise ChannelError("Paste a channel URL, not a single video")
    if path.startswith("/playlist"):
        raise ChannelError("Paste a channel URL, not a playlist")

    if not any(path.endswith(suffix) for suffix in _TAB_SUFFIXES):
        path = path + "/videos"

    return urlunparse(parsed._replace(path=path, params="", query="", fragment=""))


def list_channel_videos(url: str, limit: int) -> list[dict]:
    channel_url = normalize_channel_url(url)
    options = _with_cookies(
        {
            "extract_flat": "in_playlist",
            "quiet": True,
            "no_warnings": True,
            "skip_download": True,
            "playlistend": limit,
            "ignoreerrors": True,
        }
    )
    try:
        with yt_dlp.YoutubeDL(options) as ydl:
            info = ydl.extract_info(channel_url, download=False)
    except Exception as exc:
        raise ChannelError(f"Could not read that channel: {exc}") from exc

    if not info:
        raise ChannelError("Could not read that channel")

    channel_name = info.get("channel") or info.get("uploader") or info.get("title")
    videos: list[dict] = []
    for entry in info.get("entries") or []:
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
        raise ChannelError("No videos found for that channel")
    return videos


def max_video_height(video_id: str) -> int | None:
    """Highest video-stream height YouTube offers for this id. None if unknown."""
    options = _with_cookies(
        {
            "quiet": True,
            "no_warnings": True,
            "skip_download": True,
            "noplaylist": True,
        }
    )
    url = f"https://www.youtube.com/watch?v={video_id}"
    try:
        with yt_dlp.YoutubeDL(options) as ydl:
            info = ydl.extract_info(url, download=False)
    except Exception as exc:
        raise RuntimeError(f"Could not read video formats: {exc}") from exc
    if not info:
        return None
    heights: list[int] = []
    for fmt in info.get("formats") or []:
        height = fmt.get("height")
        vcodec = fmt.get("vcodec")
        if isinstance(height, int) and vcodec not in (None, "none"):
            heights.append(height)
    return max(heights) if heights else None


_WASTE_LIMIT_SECONDS = 90
_SPAN_SHARE = 0.15
_CONCURRENT_FRAGMENTS = "16"
_MEDIA_SUFFIXES = {".mp4", ".mkv", ".webm", ".mov"}


def use_concurrent_download(start: float, end: float, duration_seconds: int | None) -> bool:
    """Whether to fetch the whole video on many connections and trim locally.

    --download-sections goes through FFmpeg on one throttled connection, so it
    only wins when the clip is a small slice of a long upload.
    """
    if duration_seconds is None or duration_seconds <= 0:
        return True
    span = max(0.0, end - start)
    if duration_seconds - span <= _WASTE_LIMIT_SECONDS:
        return True
    return span >= _SPAN_SHARE * duration_seconds


def download_section(
    video_id: str,
    start: float,
    end: float,
    dest_stem: Path,
    *,
    output_4k: bool = False,
    title: str = "Untitled",
    duration_seconds: int | None = None,
) -> Path:
    """Download one time slice as a stream copy that lands on a nearby keyframe.

    Prefer H.264 and AAC so matching clips can be joined later without a
    re-encode.
    """
    if use_concurrent_download(start, end, duration_seconds):
        return _download_full_then_trim(video_id, start, end, dest_stem, output_4k, title)
    return _download_with_sections(video_id, start, end, dest_stem, output_4k, title)


def _download_with_sections(
    video_id: str,
    start: float,
    end: float,
    dest_stem: Path,
    output_4k: bool,
    title: str,
) -> Path:
    section = f"*{_section_clock(start)}-{_section_clock(end)}"
    command = _ytdlp_command(
        video_id,
        str(dest_stem) + ".%(ext)s",
        output_4k,
        ["--download-sections", section],
    )
    _run_ytdlp(command, output_4k, title)
    return _find_download(dest_stem)


def _download_full_then_trim(
    video_id: str,
    start: float,
    end: float,
    dest_stem: Path,
    output_4k: bool,
    title: str,
) -> Path:
    full_stem = dest_stem.parent / (dest_stem.name + "_full")
    command = _ytdlp_command(
        video_id,
        str(full_stem) + ".%(ext)s",
        output_4k,
        ["--concurrent-fragments", _CONCURRENT_FRAGMENTS],
    )
    try:
        _run_ytdlp(command, output_4k, title)
        full = _find_download(full_stem)
        dest = dest_stem.parent / (dest_stem.name + full.suffix)

        full_duration = _probe_duration(full)
        if full_duration is not None and start <= 0.05 and end >= full_duration - 0.5:
            full.replace(dest)
            return dest

        span = max(0.0, end - start)
        trim = [
            "ffmpeg",
            "-y",
            "-ss",
            f"{max(0.0, start):.3f}",
            "-i",
            str(full),
            "-t",
            f"{span:.3f}",
            "-c",
            "copy",
            "-avoid_negative_ts",
            "make_zero",
            "-movflags",
            "+faststart",
            str(dest),
        ]
        result = runner.run(trim)
        if result.returncode != 0:
            dest.unlink(missing_ok=True)
            detail = (result.stderr or result.stdout or "ffmpeg trim failed").strip()
            raise RuntimeError(detail[-800:])
        return dest
    finally:
        for leftover in full_stem.parent.glob(full_stem.name + ".*"):
            leftover.unlink(missing_ok=True)


def _ytdlp_command(
    video_id: str,
    outtmpl: str,
    output_4k: bool,
    extra: list[str],
) -> list[str]:
    return [
        sys.executable,
        "-m",
        "yt_dlp",
        "--no-playlist",
        "--no-warnings",
        *_cookies_args(),
        *extra,
        "-f",
        _format_selector(output_4k),
        "--merge-output-format",
        "mp4",
        "-o",
        outtmpl,
        f"https://www.youtube.com/watch?v={video_id}",
    ]


def _run_ytdlp(command: list[str], output_4k: bool, title: str) -> None:
    result = runner.run(command)
    if result.returncode == 0:
        return
    detail = (result.stderr or result.stdout or "yt-dlp failed").strip()
    if output_4k and "requested format is not available" in detail.lower():
        raise RuntimeError(
            f"4K export needs every video to be available in 4K. These are not: {title}"
        )
    raise RuntimeError(detail[-800:])


def _probe_duration(path: Path) -> float | None:
    command = [
        "ffprobe",
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-of",
        "default=noprint_wrappers=1:nokey=1",
        str(path),
    ]
    result = runner.run(command)
    if result.returncode != 0:
        return None
    try:
        return float((result.stdout or "").strip())
    except ValueError:
        return None


def _format_selector(output_4k: bool) -> str:
    if output_4k:
        return (
            "bv*[height>=2160][vcodec^=avc1]+ba[acodec^=mp4a]/"
            "bv*[height>=2160][vcodec^=avc1]+ba/"
            "bv*[height>=2160]+ba"
        )
    return (
        "bv*[height<=1080][vcodec^=avc1]+ba[acodec^=mp4a]/"
        "bv*[height<=1080]+ba/b[height<=1080]/b"
    )


def _with_cookies(options: dict) -> dict:
    cookiefile = _cookiefile()
    if cookiefile:
        options["cookiefile"] = cookiefile
    return options


def _cookies_args() -> list[str]:
    cookiefile = _cookiefile()
    if not cookiefile:
        return []
    return ["--cookies", cookiefile]


def _cookiefile() -> str | None:
    """Netscape cookies for YouTube, if the operator supplied them.

    YTDLP_COOKIES_FILE is a path. YTDLP_COOKIES is the file contents, or the
    same contents encoded as base64. Nothing is read from a browser.
    """
    configured = os.environ.get("YTDLP_COOKIES_FILE", "").strip()
    if configured:
        path = Path(configured)
        if not path.is_file():
            raise RuntimeError("YTDLP_COOKIES_FILE does not point at a cookies file")
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
    dest = Path(tempfile.gettempdir()) / "compcreator-youtube-cookies.txt"
    dest.write_text(text if text.endswith("\n") else text + "\n")
    dest.chmod(0o600)
    return str(dest)


def _thumbnail(entry: dict, video_id: str) -> str | None:
    thumbs = entry.get("thumbnails") or []
    if thumbs and isinstance(thumbs[-1], dict):
        url = thumbs[-1].get("url")
        if url:
            return url
    if len(video_id) == 11:
        return f"https://i.ytimg.com/vi/{video_id}/hqdefault.jpg"
    return None


def _section_clock(seconds: float) -> str:
    total = int(seconds)
    hours, rem = divmod(total, 3600)
    minutes, secs = divmod(rem, 60)
    return f"{hours}:{minutes:02d}:{secs:02d}"


def _find_download(dest_stem: Path) -> Path:
    matches = sorted(dest_stem.parent.glob(dest_stem.name + ".*"))
    media = [path for path in matches if path.suffix.lower() in _MEDIA_SUFFIXES]
    if not media:
        raise RuntimeError(f"yt-dlp did not produce a file for {dest_stem.name}")
    return media[0]
