"""Re-encode or remux one clip so it matches the compilation."""

from pathlib import Path

from app.media.plan import Prep
from app.media.probe import probe_layout
from app.media.process import _run


def _scale(width: int, height: int) -> str:
    return (
        f"scale={width}:{height}:force_original_aspect_ratio=decrease,"
        f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2,setsar=1"
    )


def _audio_encoder(codec: str) -> str:
    if codec == "opus":
        return "libopus"
    return "aac"


def normalize_clip(source: Path, dest: Path, *, output_4k: bool = False) -> None:
    """Re-encode ``source`` to a fixed H.264 and AAC file at ``dest``.

    ``output_4k`` selects a 3840×2160 frame. Otherwise the frame is 1920×1080.
    A missing ffmpeg raises ``ConfigurationError``. An encode failure raises
    ``FfmpegError``.
    """
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


def finalize_clip(source: Path, dest: Path, prep: Prep) -> None:
    """Write ``dest`` from ``source`` using the mode in ``prep``.

    ``keep`` remuxes, ``audio`` re-encodes only the audio, and ``video``
    scales and re-encodes the picture. An unknown mode raises ``ValueError``.
    """
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
