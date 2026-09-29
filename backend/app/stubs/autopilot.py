"""Stub for a later Autopilot / Idea Scout service.

Not imported by any route. Intended shape:

- A Cloud Scheduler job hits POST /internal/autopilot/scan on a cron.
- The handler reads a saved watchlist of channel URLs.
- For each channel it lists recent uploads (reuse list_channel_videos).
- A scorer (keywords, view velocity, duration) writes "ideas" to storage.
- A separate worker could turn an accepted idea into a compilation job.

Keep this off the request path that serves the manual editor. Scanning
channels on a timer needs its own quota, logging, and an explicit opt-in.
"""


# def scan_watchlist(channel_urls: list[str]) -> list[dict]:
#     raise NotImplementedError("Idea scout is not implemented")
