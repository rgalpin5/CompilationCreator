import json
import subprocess
from pathlib import Path
from typing import NamedTuple

from app.services.runner import runner


def _scale(width: int, height: int) -> str:
    return (
        f"scale={width}:{height}:force_original_aspect_ratio=decrease,"
        f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2,setsar=1"
    )


class FfmpegError(Exception):
    pass


class StreamLayout(NamedTuple):
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
    command = [
        "ffprobe",
        "-v",
        "error",
        "-show_streams",
        "-of",
        "json",
        str(path),
    ]
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode != 0:
        return None
    try:
        payload = json.loads(result.stdout)
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


def layouts_match(layouts: list[StreamLayout | None]) -> bool:
    if not layouts or any(layout is None for layout in layouts):
        return False
    first = layouts[0]
    return all(layout == first for layout in layouts)


def normalize_clip(source: Path, dest: Path, *, output_4k: bool = False) -> None:
    width, height = (3840, 2160) if output_4k else (1920, 1080)
    level = "5.1" if output_4k else "4.0"
    layout = probe_layout(source)
    has_audio = bool(layout and layout.audio_codec)
    video = _scale(width, height) + ",fps=30,format=yuv420p"
    command = ["ffmpeg", "-y", "-fflags", "+genpts", "-i", str(source)]
    if has_audio:
        command += [
            "-filter_complex",
            (
                f"[0:v:0]{video}[v];"
                "[0:a:0]aformat=sample_fmts=fltp:sample_rates=48000:channel_layouts=stereo,"
                "aresample=async=1:first_pts=0[a]"
            ),
            "-map",
            "[v]",
            "-map",
            "[a]",
        ]
    else:
        command += [
            "-f",
            "lavfi",
            "-i",
            "anullsrc=channel_layout=stereo:sample_rate=48000",
            "-filter_complex",
            f"[0:v:0]{video}[v]",
            "-map",
            "[v]",
            "-map",
            "1:a:0",
            "-shortest",
        ]
    command += [
        "-c:v",
        "libx264",
        "-preset",
        "ultrafast",
        "-crf",
        "23",
        "-profile:v",
        "high",
        "-level:v",
        level,
        "-pix_fmt",
        "yuv420p",
        "-fps_mode",
        "cfr",
        "-g",
        "60",
        "-keyint_min",
        "60",
        "-sc_threshold",
        "0",
        "-c:a",
        "aac",
        "-b:a",
        "192k",
        "-ar",
        "48000",
        "-ac",
        "2",
        "-video_track_timescale",
        "90000",
        "-avoid_negative_ts",
        "make_zero",
        "-movflags",
        "+faststart",
        str(dest),
    ]
    _run(command)


class Prep(NamedTuple):
    mode: str
    width: int
    height: int
    fps: int
    audio_codec: str
    sample_rate: str
    channels: int


PictureKey = tuple[str, int, int, str, float]
AudioKey = tuple[str, str, int]

_DEFAULT_PREP = Prep("video", 1920, 1080, 30, "aac", "48000", 2)


def _fps_bucket(frame_rate: str) -> float:
    try:
        if "/" in frame_rate:
            num, den = frame_rate.split("/", 1)
            value = float(num) / float(den)
        else:
            value = float(frame_rate)
    except (ValueError, ZeroDivisionError):
        return 0.0
    nearest = round(value)
    if abs(value - nearest) <= 0.1:
        return float(nearest)
    return round(value, 2)


def _picture_key(layout: StreamLayout) -> PictureKey:
    return (
        layout.video_codec,
        layout.width,
        layout.height,
        layout.pix_fmt,
        _fps_bucket(layout.frame_rate),
    )


def _audio_key(layout: StreamLayout) -> AudioKey:
    return (layout.audio_codec, layout.sample_rate, layout.channels)


def prep_plan(layouts: list[StreamLayout | None]) -> list[Prep]:
    present = [layout for layout in layouts if layout is not None]
    if not present:
        return [_DEFAULT_PREP for _ in layouts]

    picture_counts: dict[PictureKey, int] = {}
    for layout in present:
        key = _picture_key(layout)
        picture_counts[key] = picture_counts.get(key, 0) + 1
    target_picture = max(
        picture_counts,
        key=lambda key: (picture_counts[key], key[2], key[1]),
    )

    audio_counts: dict[AudioKey, int] = {}
    for layout in present:
        if _picture_key(layout) == target_picture:
            key = _audio_key(layout)
            audio_counts[key] = audio_counts.get(key, 0) + 1
    target_audio = max(audio_counts, key=lambda key: audio_counts[key])

    codec, width, height, _, fps_bucket = target_picture
    audio_codec, sample_rate, channels = target_audio
    fps = int(round(fps_bucket)) or 30

    modes: list[str] = []
    for layout in layouts:
        if layout is None or _picture_key(layout) != target_picture:
            modes.append("video")
        elif _audio_key(layout) != target_audio:
            modes.append("audio")
        else:
            modes.append("keep")

    if codec != "h264" and "video" in modes:
        modes = ["video"] * len(layouts)

    return [
        Prep(mode, width, height, fps, audio_codec, sample_rate, channels)
        for mode in modes
    ]


def _audio_encoder(codec: str) -> str:
    if codec == "opus":
        return "libopus"
    return "aac"


def finalize_clip(source: Path, dest: Path, prep: Prep) -> None:
    command = ["ffmpeg", "-y", "-i", str(source)]
    if prep.mode == "keep":
        command += ["-c", "copy"]
    elif prep.mode == "audio":
        command += ["-c:v", "copy", "-c:a", _audio_encoder(prep.audio_codec)]
        if prep.sample_rate:
            command += ["-ar", prep.sample_rate]
        if prep.channels:
            command += ["-ac", str(prep.channels)]
    elif prep.mode == "video":
        command += [
            "-vf",
            _scale(prep.width, prep.height),
            "-r",
            str(prep.fps),
            "-c:v",
            "libx264",
            "-preset",
            "ultrafast",
            "-crf",
            "23",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            "-ar",
            "48000",
            "-ac",
            "2",
        ]
    else:
        raise ValueError(f"Unknown prep mode: {prep.mode}")
    command += [
        "-video_track_timescale",
        "90000",
        "-movflags",
        "+faststart",
        str(dest),
    ]
    _run(command)


def concat_clips(clips: list[Path], dest: Path) -> None:
    list_file = dest.parent / "concat.txt"
    lines = []
    for clip in clips:
        escaped = str(clip.resolve()).replace("'", "'\\''")
        lines.append(f"file '{escaped}'")
    list_file.write_text("\n".join(lines) + "\n", encoding="utf-8")
    command = [
        "ffmpeg",
        "-y",
        "-f",
        "concat",
        "-safe",
        "0",
        "-i",
        str(list_file),
        "-c",
        "copy",
        "-movflags",
        "+faststart",
        str(dest),
    ]
    _run(command)


def concat_reencode(clips: list[Path], dest: Path) -> None:
    command = ["ffmpeg", "-y"]
    for clip in clips:
        command += ["-i", str(clip)]
    streams = "".join(f"[{index}:v:0][{index}:a:0]" for index in range(len(clips)))
    command += [
        "-filter_complex",
        f"{streams}concat=n={len(clips)}:v=1:a=1[v][a]",
        "-map",
        "[v]",
        "-map",
        "[a]",
        "-c:v",
        "libx264",
        "-preset",
        "ultrafast",
        "-crf",
        "23",
        "-pix_fmt",
        "yuv420p",
        "-fps_mode",
        "cfr",
        "-c:a",
        "aac",
        "-ar",
        "48000",
        "-ac",
        "2",
        "-video_track_timescale",
        "90000",
        "-movflags",
        "+faststart",
        str(dest),
    ]
    _run(command)


def _run(command: list[str]) -> None:
    result = runner.run(command)
    if result.returncode != 0:
        detail = (result.stderr or result.stdout or "ffmpeg failed").strip()
        raise FfmpegError(detail[-800:])
