"""Download, prepare, and join one compilation."""

import contextlib
import contextvars
import logging
import shutil
import threading
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from app.errors import ConfigurationError, terminal_message
from app.hardware import download_workers, prepare_workers
from app.jobs.runner import JobCancelled, runner
from app.jobs.store import JobStore
from app.media.concat import concat_clips, concat_reencode
from app.media.encode import finalize_clip, normalize_clip
from app.media.plan import fit_4k, prep_plan
from app.media.probe import probe_layout
from app.media.process import FfmpegError
from app.models import Clip
from app.timeparse import parse_timestamp
from app.usage.store import UsageStore
from app.youtube.download import download_section

log = logging.getLogger("compcreator.compilation")


def _run_parallel[T](
    job_id: str,
    count: int,
    max_workers: int,
    work: Callable[[int], T],
) -> list[T]:
    results: list[T | None] = [None] * count
    pool = ThreadPoolExecutor(max_workers=max(1, max_workers))
    finished = False
    try:
        futures = {
            pool.submit(contextvars.copy_context().run, work, index): index
            for index in range(count)
        }
        for future in as_completed(futures):
            results[futures[future]] = future.result()
        finished = True
    finally:
        if not finished:
            # yt-dlp runs in this process, so killing child processes alone
            # cannot stop a sibling download. Marking the job cancelled makes
            # each worker stop at its next checkpoint or progress hook.
            with contextlib.suppress(OSError):
                runner.cancel(job_id)
        # Wait for running workers so none of them writes into the job folder
        # after the caller deletes it.
        pool.shutdown(wait=True, cancel_futures=True)
    completed: list[T] = []
    for item in results:
        if item is None:
            raise RuntimeError("A clip finished without producing a file.")
        completed.append(item)
    return completed


def _record_usage(usage: UsageStore, ordered: list[Clip], job_id: str) -> str | None:
    """Log ``ordered`` as one finished compilation and return its file name.

    A usage log that cannot be written is logged and skipped. The video is
    already finished, so the export still succeeds.
    """
    duration = sum(parse_timestamp(clip.end) - parse_timestamp(clip.start) for clip in ordered)
    try:
        return usage.record(
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
    except OSError:
        log.exception("Could not write the usage log for export %s", job_id)
        return None


def _download_all(
    store: JobStore,
    job_id: str,
    ordered: list[Clip],
    job_dir: Path,
    output_4k: bool,
) -> list[Path]:
    """Download every clip in parallel and return the raw files in timeline order."""
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

    return _run_parallel(job_id, total, download_workers(total), download)


def _prepare_all(
    store: JobStore,
    job_id: str,
    raws: list[Path],
    job_dir: Path,
    output_4k: bool,
) -> list[Path]:
    """Bring every raw clip to the common layout and return the parts in order."""
    total = len(raws)
    runner.checkpoint()
    layouts = [probe_layout(path) for path in raws]
    plan = prep_plan(layouts)
    if output_4k:
        plan = fit_4k(plan, layouts)
    labels = {
        "audio": "Matching audio on clip {i} of {n}",
        "video": (
            "Scaling clip {i} of {n} to 4K"
            if output_4k
            else "Re-encoding clip {i} of {n} so the formats match"
        ),
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

    encodes_video = any(prep.mode == "video" for prep in plan)
    return _run_parallel(
        job_id,
        total,
        prepare_workers(total, encodes_video=encodes_video),
        prepare,
    )


def _join(
    store: JobStore,
    job_id: str,
    parts: list[Path],
    raws: list[Path],
    job_dir: Path,
    output_4k: bool,
) -> Path:
    """Join ``parts`` into compilation.mp4, falling back to normalized re-encodes."""
    output = job_dir / "compilation.mp4"
    runner.checkpoint()
    store.update(job_id, status="concatenating", progress="Joining clips")
    try:
        concat_clips(parts, output)
        return output
    except FfmpegError as exc:
        log.info("Export %s: stream copy join failed, re-encoding instead: %s", job_id, exc)
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
    output.unlink(missing_ok=True)
    store.update(job_id, status="concatenating", progress="Joining clips")
    try:
        concat_clips(normalized, output)
    except FfmpegError:
        output.unlink(missing_ok=True)
        store.update(job_id, status="concatenating", progress="Joining clips")
        concat_reencode(normalized, output)
    return output


def _remove_working_files(job_dir: Path, *, keep: Path) -> None:
    """Delete everything in ``job_dir`` except ``keep``.

    A ready job can wait up to a day for its download, and on Cloud Run the
    job folder is held in memory, so the raw clips and parts must not wait
    with it.
    """
    for entry in job_dir.iterdir():
        if entry == keep:
            continue
        if entry.is_dir():
            shutil.rmtree(entry, ignore_errors=True)
        else:
            entry.unlink(missing_ok=True)


def _finish(
    store: JobStore,
    job_id: str,
    ordered: list[Clip],
    output: Path,
    job_dir: Path,
    usage: UsageStore | None,
) -> None:
    """Record usage, then mark the job ready."""
    runner.checkpoint()
    if usage:
        name = _record_usage(usage, ordered, job_id)
        if name:
            store.update(job_id, filename=name)
    # Ready comes last so a save never sees the job before its file name.
    store.update(
        job_id,
        status="ready",
        progress="Ready",
        error=None,
        output_path=str(output),
    )
    if _cancelled_in_store(store, job_id):
        # Cancel arrived after the last checkpoint. The ready update was
        # ignored, so the finished file would otherwise stay on disk. The store
        # is checked rather than the runner because the cancel route marks the
        # store first and may not have reached the runner yet.
        shutil.rmtree(job_dir, ignore_errors=True)


def _cancelled_in_store(store: JobStore, job_id: str) -> bool:
    job = store.get(job_id)
    return job is not None and job["status"] == "cancelled"


def run_compilation(
    store: JobStore,
    job_id: str,
    clips: list[Clip],
    output_4k: bool = False,
    usage: UsageStore | None = None,
) -> None:
    """Download, prepare, and join ``clips`` for ``job_id``.

    The job record is updated as the work moves from downloading to ready.
    Cancellation deletes the working folder. A missing program, a denied
    permission, a bad setting, or a media failure is stored on the job as a
    short message and does not leave a traceback in that message. The store
    is told when this returns, so the next export can start.
    """
    try:
        _run(store, job_id, clips, output_4k, usage)
    finally:
        store.worker_stopped(job_id)


def _run(
    store: JobStore,
    job_id: str,
    clips: list[Clip],
    output_4k: bool,
    usage: UsageStore | None,
) -> None:
    # Bind before reading the job. A cancel that reaches the runner before
    # this bind is ignored there, but it marked the store first, so the read
    # below sees it.
    token = runner.bind(job_id)
    try:
        job = store.get(job_id)
        if not job:
            return
        job_dir = Path(job["dir"])
        if job["status"] == "cancelled":
            shutil.rmtree(job_dir, ignore_errors=True)
            return
        _export(store, job_id, clips, job_dir, output_4k, usage)
    finally:
        runner.unbind(token)
        runner.forget(job_id)


def _export(
    store: JobStore,
    job_id: str,
    clips: list[Clip],
    job_dir: Path,
    output_4k: bool,
    usage: UsageStore | None,
) -> None:
    ordered = sorted(clips, key=lambda clip: clip.order)
    try:
        raws = _download_all(store, job_id, ordered, job_dir, output_4k)
        parts = _prepare_all(store, job_id, raws, job_dir, output_4k)
        output = _join(store, job_id, parts, raws, job_dir, output_4k)
        _remove_working_files(job_dir, keep=output)
        _finish(store, job_id, ordered, output, job_dir, usage)
    except JobCancelled:
        shutil.rmtree(job_dir, ignore_errors=True)
        store.update(
            job_id,
            status="cancelled",
            progress="Cancelled",
            error=None,
            output_path=None,
        )
    except (FfmpegError, ConfigurationError, OSError, RuntimeError, ValueError) as exc:
        # Workers have stopped by now, so nothing is still writing here.
        shutil.rmtree(job_dir, ignore_errors=True)
        store.update(
            job_id,
            status="failed",
            progress="Failed",
            error=terminal_message(exc)[:800],
        )
    except Exception:
        log.exception("Export %s failed", job_id)
        shutil.rmtree(job_dir, ignore_errors=True)
        store.update(
            job_id,
            status="failed",
            progress="Failed",
            error="The export stopped because of an internal error.",
        )
