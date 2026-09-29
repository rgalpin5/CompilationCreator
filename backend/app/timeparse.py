import re

_TIMESTAMP = re.compile(r"^(?:(\d+):)?(\d{1,2}):(\d{2})$")


def parse_timestamp(value: str) -> float:
    """Parse mm:ss or hh:mm:ss into seconds."""
    text = value.strip()
    match = _TIMESTAMP.fullmatch(text)
    if not match:
        raise ValueError(f"Time must be mm:ss or hh:mm:ss, got {value!r}")
    hours = int(match.group(1) or 0)
    minutes = int(match.group(2))
    seconds = int(match.group(3))
    if minutes > 59 or seconds > 59:
        raise ValueError(f"Invalid clock time {value!r}")
    return float(hours * 3600 + minutes * 60 + seconds)


def format_timestamp(seconds: float) -> str:
    total = int(seconds)
    hours, rem = divmod(total, 3600)
    minutes, secs = divmod(rem, 60)
    if hours:
        return f"{hours}:{minutes:02d}:{secs:02d}"
    return f"{minutes:02d}:{secs:02d}"
