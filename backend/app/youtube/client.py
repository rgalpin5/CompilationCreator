"""YoutubeDL option dict and the download call."""

import yt_dlp

from app.errors import terminal_message
from app.jobs.runner import JobCancelled, runner
from app.youtube.cookies import YtdlpOptions, _with_cookies, private_cookies
from app.youtube.failures import YTDLP_ERRORS
from app.youtube.formats import _format_selector


def _watch_url(video_id: str) -> str:
    return f"https://www.youtube.com/watch?v={video_id}"


def _ytdlp_options(outtmpl: str, output_4k: bool, extra: YtdlpOptions) -> YtdlpOptions:
    options = {
        "noplaylist": True,
        "no_warnings": True,
        "quiet": True,
        "noprogress": True,
        "overwrites": True,
        "format": _format_selector(output_4k),
        "merge_output_format": "mp4",
        "outtmpl": outtmpl,
    }
    options.update(extra)
    return _with_cookies(options)


def _run_ytdlp(options: YtdlpOptions, url: str) -> None:
    def _hook(_status: YtdlpOptions) -> None:
        runner.checkpoint()

    options["progress_hooks"] = [_hook]
    try:
        with private_cookies(options) as run_options, yt_dlp.YoutubeDL(run_options) as ydl:
            ydl.download([url])
    except JobCancelled:
        raise
    except YTDLP_ERRORS as exc:
        detail = str(exc).strip() or "yt-dlp failed"
        raise RuntimeError(detail[-800:]) from exc
    except OSError as exc:
        raise RuntimeError(terminal_message(exc)) from exc
