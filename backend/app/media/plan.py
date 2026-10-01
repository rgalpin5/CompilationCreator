"""Decide which clips can be copied and which must be re-encoded."""

from collections.abc import Sequence
from typing import NamedTuple

from app.media.probe import StreamLayout


class Prep(NamedTuple):
    """How one clip should be prepared before it is joined."""

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


def prep_plan(layouts: Sequence[StreamLayout | None]) -> list[Prep]:
    """Choose copy, audio remux, or picture re-encode for each layout.

    The most common picture and audio pair is the target. Clips that already
    match it are copied. A missing layout is re-encoded.
    """
    present = [layout for layout in layouts if layout is not None]
    if not present:
        return [_DEFAULT_PREP for _ in layouts]

    picture_counts: dict[PictureKey, int] = {}
    for item in present:
        picture_key = _picture_key(item)
        picture_counts[picture_key] = picture_counts.get(picture_key, 0) + 1
    target_picture = max(
        picture_counts,
        key=lambda key: (picture_counts[key], key[2], key[1]),
    )

    audio_counts: dict[AudioKey, int] = {}
    for item in present:
        if _picture_key(item) == target_picture:
            audio_key = _audio_key(item)
            audio_counts[audio_key] = audio_counts.get(audio_key, 0) + 1
    target_audio = max(audio_counts, key=lambda key: audio_counts[key])

    codec, width, height, _, fps_bucket = target_picture
    audio_codec, sample_rate, channels = target_audio
    fps = round(fps_bucket) or 30

    modes: list[str] = []
    for candidate in layouts:
        if candidate is None or _picture_key(candidate) != target_picture:
            modes.append("video")
        elif _audio_key(candidate) != target_audio:
            modes.append("audio")
        else:
            modes.append("keep")

    if codec != "h264" and "video" in modes:
        modes = ["video"] * len(layouts)

    return [Prep(mode, width, height, fps, audio_codec, sample_rate, channels) for mode in modes]


def fit_4k(plan: Sequence[Prep], layouts: Sequence[StreamLayout | None]) -> list[Prep]:
    """Scale every clip onto a 3840×2160 frame.

    A clip that is already that size keeps its current prep. Anything smaller
    is re-encoded with a plain scale, which does not add picture detail.
    """
    fitted: list[Prep] = []
    for prep, layout in zip(plan, layouts, strict=True):
        already = layout is not None and layout.width == 3840 and layout.height == 2160
        mode = prep.mode if already else "video"
        fitted.append(prep._replace(mode=mode, width=3840, height=2160))
    return fitted
