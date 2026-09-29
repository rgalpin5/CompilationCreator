import contextvars
import shutil
import threading
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import TypeVar

from app.config import MAX_CLIP_SECONDS, MAX_TOTAL_SECONDS
from app.models import Clip
from app.services.ffmpeg_service import (
    FfmpegError,
    concat_clips,
    finalize_clip,
    normalize_clip,
    prep_plan,
    probe_layout,
)
from app.services.job_store import JobStore
from app.services.runner import JobCancelled, runner
from app.services.usage_store import UsageStore
from app.services.ytdlp_service import download_section
from app.timeparse import parse_timestamp

FOUR_K_HEIGHT = 2160
T = TypeVar("T")


def validate_timeline(clips: list[Clip]) -> list[Clip]:
    if not clips:
        raise ValueError("Add at least one clip")

    total = 0.0
    for clip in clips:
        start = parse_timestamp(clip.start)
        end = parse_timestamp(clip.end)
        if end <= start:
            raise ValueError(f"End time must be after start for “{clip.title}”")
        duration = end - start
        if duration > MAX_CLIP_SECONDS:
            raise ValueError(f"Each video must be 35 minutes or less (“{clip.title}”)")
        total += duration

    if total > MAX_TOTAL_SECONDS:
        raise ValueError("The compilation must be 4 hours 40 minutes or less")

    return sorted(clips, key=lambda clip: clip.order)


def videos_missing_4k(heights: list[tuple[str, int | None]]) -> list[str]:
    return [title for title, height in heights if height is None or height < FOUR_K_HEIGHT]


def _run_parallel(
    job_id: str,
    count: int,
    max_workers: int,
    work: Callable[[int], T],
) -> list[T]:
    results: list[T | None] = [None] * count
    pool = ThreadPoolExecutor(max_workers=max(1, max_workers))
    try:
        futures = {
            pool.submit(contextvars.copy_context().run, work, index): index
            for index in range(count)
        }
        for future in as_completed(futures):
            results[futures[future]] = future.result()
    except JobCancelled:
        raise
    except BaseException:
        runner.kill(job_id)
        raise
    finally:
        pool.shutdown(wait=False, cancel_futures=True)
    return results  # type: ignore[return-value]


def run_compilation(
    store: JobStore,
    job_id: str,
    clips: list[Clip],
    output_4k: bool = False,
    usage: UsageStore | None = None,
) -> None:
    job = store.get(job_id)
    if not job:
        return
    job_dir = Path(job["dir"])
    ordered = sorted(clips, key=lambda clip: clip.order)
    token = runner.bind(job_id)

    try:
        total = len(ordered)
        store.update(
            job_id,
            status="downloading",
            progress=f"Downloading clips (0 of {total} finished)",
        )
        done = 0
        done_lock = threading.Lock()

        def download(index: int) -> Path:
            nonlocal done
            clip = ordered[index]
            runner.checkpoint()
            path = download_section(
                clip.video_id,
                parse_timestamp(clip.start),
                parse_timestamp(clip.end),
                job_dir / f"raw_{index + 1:03d}",
                output_4k=output_4k,
                title=clip.title,
                duration_seconds=clip.duration_seconds,
            )
            with done_lock:
                done += 1
                store.update(
                    job_id,
                    status="downloading",
                    progress=f"Downloading clips ({done} of {total} finished)",
                )
            return path

        raws = _run_parallel(job_id, total, min(4, total), download)

        runner.checkpoint()
        layouts = [probe_layout(path) for path in raws]
        if output_4k:
            missing = videos_missing_4k(
                [
                    (clip.title, layout.height if layout else None)
                    for clip, layout in zip(ordered, layouts)
                ]
            )
            if missing:
                names = ", ".join(missing)
                raise RuntimeError(
                    "4K export needs every video to be available in 4K. "
                    f"These are not: {names}"
                )

        plan = prep_plan(layouts)
        labels = {
            "audio": "Matching audio on clip {i} of {n}",
            "video": "Re-encoding clip {i} of {n} so the formats match",
            "keep": "Preparing clip {i} of {n}",
        }

        def prepare(index: int) -> Path:
            runner.checkpoint()
            prep = plan[index]
            store.update(
                job_id,
                status="downloading",
                progress=labels[prep.mode].format(i=index + 1, n=total),
            )
            part = job_dir / f"part_{index + 1:03d}.mp4"
            finalize_clip(raws[index], part, prep)
            return part

        prep_workers = 2 if any(prep.mode == "video" for prep in plan) else 4
        parts = _run_parallel(job_id, total, min(prep_workers, total), prepare)

        output = job_dir / "compilation.mp4"
        runner.checkpoint()
        store.update(job_id, status="concatenating", progress="Joining clips")
        try:
            concat_clips(parts, output)
        except FfmpegError:
            normalized: list[Path] = []
            for index, raw in enumerate(raws, start=1):
                runner.checkpoint()
                store.update(
                    job_id,
                    status="downloading",
                    progress=f"Re-encoding clip {index} of {len(raws)} so the formats match",
                )
                norm = job_dir / f"norm_{index:03d}.mp4"
                normalize_clip(raw, norm, output_4k=output_4k)
                normalized.append(norm)
            store.update(job_id, status="concatenating", progress="Joining clips")
            concat_clips(normalized, output)
        store.update(
            job_id,
            status="ready",
            progress="Ready",
            error=None,
            output_path=str(output),
        )
        finished = store.get(job_id)
        if usage and finished and finished["status"] == "ready":
            duration = sum(
                parse_timestamp(clip.end) - parse_timestamp(clip.start) for clip in ordered
            )
            usage.record(
                [
                    {
                        "video_id": clip.video_id,
                        "title": clip.title,
                        "channel": clip.channel,
                        "view_count": clip.view_count,
                        "duration_seconds": clip.duration_seconds,
                        "thumbnail": clip.thumbnail,
                    }
                    for clip in ordered
                ],
                duration_seconds=int(duration),
            )
    except JobCancelled:
        shutil.rmtree(job_dir, ignore_errors=True)
        store.update(
            job_id,
            status="cancelled",
            progress="Cancelled",
            error=None,
            output_path=None,
        )
    except Exception as exc:
        store.update(
            job_id,
            status="failed",
            progress="Failed",
            error=str(exc)[:800],
        )
    finally:
        runner.unbind(token)
