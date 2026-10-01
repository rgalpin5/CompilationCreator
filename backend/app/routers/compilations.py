import threading
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request
from fastapi.responses import FileResponse
from starlette.background import BackgroundTask

from app.auth import file_token
from app.compilation.pipeline import run_compilation
from app.compilation.validate import validate_timeline
from app.config import settings
from app.delivery import (
    default_download_dir,
    deliver_compilation,
    remove_job_folder,
    resolve_directory,
    safe_filename,
)
from app.errors import terminal_message
from app.jobs.runner import runner
from app.jobs.store import JobStore
from app.models import CompilationRequest, DownloadRequest, JobStatus
from app.records import JobRecord
from app.routers.deps import get_job_store, get_usage_store
from app.usage.store import UsageStore

_ACTIVE = {"queued", "downloading", "concatenating"}
# A browser download stays available while saved, until the grace period ends.
_DOWNLOADABLE = {"ready", "saved"}
BROWSER_DOWNLOAD_GRACE_SECONDS = 600.0

router = APIRouter()
_save_lock = threading.Lock()


@router.post("/compilations", status_code=202, response_model=JobStatus)
def create_compilation(
    body: CompilationRequest,
    background_tasks: BackgroundTasks,
    job_store: JobStore = Depends(get_job_store),
    usage_store: UsageStore = Depends(get_usage_store),
) -> JobStatus:
    """Start an export and return the queued job."""
    try:
        clips = validate_timeline(body.clips)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    job = job_store.create_if_idle()
    if job is None:
        raise HTTPException(
            status_code=409,
            detail="Another export is still running. Wait for it to finish or cancel it.",
        )
    background_tasks.add_task(
        run_compilation, job_store, job["id"], clips, body.output_4k, usage_store
    )
    return _public(job)


@router.get("/compilations/{job_id}", response_model=JobStatus)
def compilation_status(
    job_id: str,
    job_store: JobStore = Depends(get_job_store),
) -> JobStatus:
    """Return the current status of ``job_id``."""
    job = job_store.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return _public(job)


@router.post("/compilations/{job_id}/cancel", response_model=JobStatus)
def cancel_compilation(
    job_id: str,
    job_store: JobStore = Depends(get_job_store),
) -> JobStatus:
    """Stop ``job_id`` when it is still queued, downloading, or joining."""
    job = job_store.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job["status"] not in _ACTIVE:
        raise HTTPException(status_code=409, detail="That export is no longer running")
    job_store.update(job_id, status="cancelled", progress="Cancelled", error=None, output_path=None)
    # The export removes its own folder once its workers have stopped.
    # Deleting it here would race downloads that are still writing.
    runner.cancel(job_id)
    cancelled = job_store.get(job_id)
    if not cancelled:
        raise HTTPException(status_code=404, detail="Job not found")
    return _public(cancelled)


@router.get("/download-folder")
def download_folder() -> dict[str, str]:
    """The default folder a finished video is saved into."""
    return {"path": str(default_download_dir())}


@router.post("/compilations/{job_id}/download", response_model=JobStatus)
def download_compilation(
    job_id: str,
    body: DownloadRequest | None = None,
    job_store: JobStore = Depends(get_job_store),
) -> JobStatus:
    """Copy the finished video to Downloads or a chosen folder, then delete the job."""
    if settings.hosted:
        # Downloads here would be the server's own folder, out of the user's reach.
        raise HTTPException(
            status_code=409,
            detail="This server sends the video to your browser. Use the download link.",
        )
    with _save_lock:
        job = job_store.get(job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        if job.get("saved_path"):
            raise HTTPException(status_code=409, detail="That video was already saved")
        output_path = job.get("output_path")
        if job["status"] != "ready" or not output_path:
            raise HTTPException(status_code=404, detail="Compilation is not ready")
        try:
            directory = resolve_directory(
                body.directory if body else None,
                allow_custom=not settings.hosted,
            )
            saved = deliver_compilation(
                output_path,
                job["dir"],
                directory,
                job.get("filename"),
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except FileNotFoundError as exc:
            raise HTTPException(status_code=404, detail=terminal_message(exc)) from exc
        except OSError as exc:
            raise HTTPException(status_code=500, detail=terminal_message(exc)) from exc
        job_store.update(
            job_id,
            status="saved",
            progress="Saved",
            error=None,
            output_path=None,
            saved_path=str(saved),
        )
        saved_job = job_store.get(job_id)
        if not saved_job:
            raise HTTPException(status_code=404, detail="Job not found")
        return _public(saved_job)


@router.get("/compilations/{job_id}/file")
def compilation_file(
    job_id: str,
    request: Request,
    job_store: JobStore = Depends(get_job_store),
) -> FileResponse:
    """Send the finished video to the browser, then delete the job after a grace period.

    A full response marks the job saved and keeps the file for
    ``BROWSER_DOWNLOAD_GRACE_SECONDS`` so an interrupted download can be retried.
    """
    job = job_store.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    output_path = job.get("output_path")
    if job["status"] not in _DOWNLOADABLE or not output_path:
        raise HTTPException(status_code=404, detail="Compilation is not ready")
    if not Path(output_path).is_file():
        raise HTTPException(status_code=404, detail="Compilation file is missing")
    # Starlette runs the background task after any response, including a
    # partial range, so only a full request may start the countdown.
    finish = None
    if "range" not in request.headers:
        finish = BackgroundTask(_finish_browser_download, job_store, job_id)
    return FileResponse(
        output_path,
        media_type="video/mp4",
        filename=safe_filename(job.get("filename")),
        background=finish,
    )


def _finish_browser_download(job_store: JobStore, job_id: str) -> None:
    """Mark ``job_id`` downloaded and schedule its working files for deletion.

    Every byte reaching the socket does not prove the browser kept the file:
    uvicorn buffers the tail and drops it silently when the client leaves.
    """
    with _save_lock:
        job = job_store.get(job_id)
        if not job or job["status"] != "ready":
            return
        job_store.update(job_id, status="saved", progress="Downloaded", error=None)
    timer = threading.Timer(
        BROWSER_DOWNLOAD_GRACE_SECONDS, _expire_browser_download, (job_store, job_id)
    )
    timer.daemon = True
    timer.start()


def _expire_browser_download(job_store: JobStore, job_id: str) -> None:
    """Delete a browser-downloaded job's files once its grace period ends."""
    with _save_lock:
        job = job_store.get(job_id)
        if not job or job["status"] != "saved" or not job.get("output_path"):
            return
        job_store.update(job_id, output_path=None)
        remove_job_folder(job["dir"])


def _public(job: JobRecord) -> JobStatus:
    """The job fields the API returns. Working paths stay on the server."""
    download_url = None
    file_url = None
    if job.get("output_path"):
        if settings.hosted and job["status"] in _DOWNLOADABLE:
            file_url = f"/api/compilations/{job['id']}/file"
            # A download link cannot send the password header, so it carries
            # a token that unlocks only this job's file.
            token = file_token(job["id"])
            if token:
                file_url = f"{file_url}?token={token}"
        elif job["status"] == "ready":
            download_url = f"/api/compilations/{job['id']}/download"
    return JobStatus(
        id=job["id"],
        status=job["status"],
        progress=job["progress"],
        error=job.get("error"),
        download_url=download_url,
        file_url=file_url,
        saved_path=job.get("saved_path"),
    )
