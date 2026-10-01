"""Choose a section download or a full-file download plus a local trim."""

from pathlib import Path

from yt_dlp.utils import download_range_func

from app.errors import ConfigurationError
from app.hardware import fragment_connections
from app.jobs.runner import runner
from app.media.probe import _probe_duration
from app.youtube.client import _run_ytdlp, _watch_url, _ytdlp_options

_WASTE_LIMIT_SECONDS = 90
_SPAN_SHARE = 0.15
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
    duration_seconds: int | None = None,
) -> Path:
    """Download one time slice as a stream copy that lands on a nearby keyframe.

    Prefer H.264 and AAC so matching clips can be joined later without a
    re-encode.
    """
    if use_concurrent_download(start, end, duration_seconds):
        return _download_full_then_trim(video_id, start, end, dest_stem, output_4k)
    return _download_with_sections(video_id, start, end, dest_stem, output_4k)


def _download_with_sections(
    video_id: str,
    start: float,
    end: float,
    dest_stem: Path,
    output_4k: bool,
) -> Path:
    options = _ytdlp_options(
        str(dest_stem) + ".%(ext)s",
        output_4k,
        {"download_ranges": download_range_func([], [(start, end)])},
    )
    _run_ytdlp(options, _watch_url(video_id))
    return _find_download(dest_stem)


def _download_full_then_trim(
    video_id: str,
    start: float,
    end: float,
    dest_stem: Path,
    output_4k: bool,
) -> Path:
    full_stem = dest_stem.parent / (dest_stem.name + "_full")
    options = _ytdlp_options(
        str(full_stem) + ".%(ext)s",
        output_4k,
        {"concurrent_fragment_downloads": fragment_connections()},
    )
    try:
        _run_ytdlp(options, _watch_url(video_id))
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
        try:
            result = runner.run(trim)
        except FileNotFoundError as exc:
            raise ConfigurationError(
                "ffmpeg was not found. Install ffmpeg and make sure it is on PATH."
            ) from exc
        if result.returncode != 0:
            dest.unlink(missing_ok=True)
            detail = (result.stderr or result.stdout or "ffmpeg trim failed").strip()
            raise RuntimeError(detail[-800:])
        return dest
    finally:
        for leftover in full_stem.parent.glob(full_stem.name + ".*"):
            leftover.unlink(missing_ok=True)


def _find_download(dest_stem: Path) -> Path:
    matches = sorted(dest_stem.parent.glob(dest_stem.name + ".*"))
    media = [path for path in matches if path.suffix.lower() in _MEDIA_SUFFIXES]
    if not media:
        raise RuntimeError(f"yt-dlp did not produce a file for {dest_stem.name}")
    return media[0]
