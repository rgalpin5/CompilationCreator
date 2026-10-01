"""ffprobe layout and duration."""

import json
import subprocess
from pathlib import Path
from typing import Any, NamedTuple

from app.errors import ConfigurationError
from app.jobs.runner import runner


class StreamLayout(NamedTuple):
    """Codec, picture, and audio fields that decide whether clips can be copied."""
    video_codec: str
    width: int
    height: int
    pix_fmt: str
    frame_rate: str
    time_base: str
    profile: str
    audio_codec: str
    sample_rate: str
    channels: int
    audio_time_base: str


def probe_layout(path: Path) -> StreamLayout | None:
    """Read the video and audio layout of ``path``.

    Returns ``None`` when the file has no video stream or ffprobe cannot read
    it. A missing ffprobe program raises ``ConfigurationError``.
    """
    command = [
        "ffprobe",
        "-v",
        "error",
        "-show_streams",
        "-of",
        "json",
        str(path),
    ]
    try:
        result = subprocess.run(command, capture_output=True, text=True, check=False)
    except FileNotFoundError as exc:
        raise ConfigurationError(
            "ffprobe was not found. Install ffmpeg and make sure it is on PATH."
        ) from exc
    if result.returncode != 0:
        return None
    try:
        payload: Any = json.loads(result.stdout)
    except json.JSONDecodeError:
        return None
    streams = payload.get("streams") or []
    video = next((stream for stream in streams if stream.get("codec_type") == "video"), None)
    if not video:
        return None
    audio = next((stream for stream in streams if stream.get("codec_type") == "audio"), None)
    return StreamLayout(
        video_codec=str(video.get("codec_name") or ""),
        width=int(video.get("width") or 0),
        height=int(video.get("height") or 0),
        pix_fmt=str(video.get("pix_fmt") or ""),
        frame_rate=str(video.get("avg_frame_rate") or ""),
        time_base=str(video.get("time_base") or ""),
        profile=str(video.get("profile") or ""),
        audio_codec=str((audio or {}).get("codec_name") or ""),
        sample_rate=str((audio or {}).get("sample_rate") or ""),
        channels=int((audio or {}).get("channels") or 0),
        audio_time_base=str((audio or {}).get("time_base") or ""),
    )


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
