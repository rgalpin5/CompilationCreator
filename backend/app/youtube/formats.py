"""yt-dlp format strings for a 1080p or 4K source."""


def _format_selector(output_4k: bool) -> str:
    if output_4k:
        # Prefer a real 4K source. If YouTube does not have one, take the
        # largest smaller size and let ffmpeg scale it to 3840x2160.
        return (
            "bv*[height<=2160][vcodec^=avc1]+ba[acodec^=mp4a]/"
            "bv*[height<=2160][vcodec^=avc1]+ba/"
            "bv*[height<=2160]+ba/"
            "b"
        )
    return "bv*[height<=1080][vcodec^=avc1]+ba[acodec^=mp4a]/bv*[height<=1080]+ba/b[height<=1080]/b"
