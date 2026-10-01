"""Join prepared clips with the concat demuxer, or a filter re-encode."""

from pathlib import Path

from app.media.process import _run


def _concat_line(path: Path) -> str:
    """One concat-demuxer entry.

    The demuxer treats a backslash as an escape. Forward slashes are a valid
    path on Windows and Unix, so the same line works on both.
    """
    text = path.resolve().as_posix().replace("'", "'\\''")
    return f"file '{text}'"


def concat_clips(clips: list[Path], dest: Path) -> None:
    """Join ``clips`` into ``dest`` by stream copy.

    Writes ``concat.txt`` beside ``dest``. ffmpeg failure raises ``FfmpegError``.
    A missing ffmpeg raises ``ConfigurationError``.
    """
    list_file = dest.parent / "concat.txt"
    lines = [_concat_line(clip) for clip in clips]
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
    """Join ``clips`` into ``dest`` by decoding and encoding them together.

    Used when stream copy cannot produce a playable file. ffmpeg failure
    raises ``FfmpegError``.
    """
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
