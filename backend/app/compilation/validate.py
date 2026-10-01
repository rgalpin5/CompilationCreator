"""Check a timeline before an export starts."""

from app.models import Clip
from app.timeparse import parse_timestamp

FOUR_K_HEIGHT = 2160
# Each clip can exist three times on disk (download, prepared part, joined
# file), so these bound how much one export can write.
MAX_CLIPS = 100
MAX_TOTAL_SECONDS = 4 * 60 * 60


def validate_timeline(clips: list[Clip]) -> list[Clip]:
    """Return ``clips`` in timeline order.

    An empty or oversized timeline, or a clip whose end is not after its
    start, raises ``ValueError`` with a message that names the problem.
    """
    if not clips:
        raise ValueError("Add at least one clip")
    if len(clips) > MAX_CLIPS:
        raise ValueError(f"An export can have at most {MAX_CLIPS} clips")

    total = 0.0
    for clip in clips:
        start = parse_timestamp(clip.start)
        end = parse_timestamp(clip.end)
        if end <= start:
            raise ValueError(f"End time must be after start for “{clip.title}”")
        total += end - start
    if total > MAX_TOTAL_SECONDS:
        hours = MAX_TOTAL_SECONDS // 3600
        raise ValueError(f"An export can be at most {hours} hours long. Shorten or remove clips.")

    return sorted(clips, key=lambda clip: clip.order)


def videos_missing_4k(heights: list[tuple[str, int | None]]) -> list[str]:
    """Titles whose known height is below 2160, or whose height was not reported."""
    return [title for title, height in heights if height is None or height < FOUR_K_HEIGHT]
