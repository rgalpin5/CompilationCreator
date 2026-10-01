"""Check a timeline before an export starts."""

from app.models import Clip
from app.timeparse import parse_timestamp

FOUR_K_HEIGHT = 2160


def validate_timeline(clips: list[Clip]) -> list[Clip]:
    """Return ``clips`` in timeline order.

    An empty timeline, or a clip whose end is not after its start, raises
    ``ValueError`` with a message that names the problem.
    """
    if not clips:
        raise ValueError("Add at least one clip")

    for clip in clips:
        start = parse_timestamp(clip.start)
        end = parse_timestamp(clip.end)
        if end <= start:
            raise ValueError(f"End time must be after start for “{clip.title}”")

    return sorted(clips, key=lambda clip: clip.order)


def videos_missing_4k(heights: list[tuple[str, int | None]]) -> list[str]:
    """Titles whose known height is below 2160, or whose height was not reported."""
    return [title for title, height in heights if height is None or height < FOUR_K_HEIGHT]
