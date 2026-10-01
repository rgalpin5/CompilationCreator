import threading

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from fastapi.responses import JSONResponse

from app.compilation.pipeline import run_compilation
from app.compilation.validate import validate_timeline
from app.config import settings
from app.delivery import default_download_dir, deliver_compilation, resolve_directory
from app.errors import terminal_message
from app.jobs.runner import runner
from app.jobs.store import JobStore
from app.models import CompilationRequest, DownloadRequest, JobStatus
from app.records import JobRecord
from app.routers.deps import get_job_store, get_usage_store
from app.usage.store import UsageStore

_ACTIVE = {"queued", "downloading", "concatenating"}

router = APIRouter()
_save_lock = threading.Lock()


@router.post("/compilations", status_code=202)
def create_compilation(
    body: CompilationRequest,
    background_tasks: BackgroundTasks,
    job_store: JobStore = Depends(get_job_store),
    usage_store: UsageStore = Depends(get_usage_store),
) -> JSONResponse:
    """Start an export and return the queued job."""
    try:
        clips = validate_timeline(body.clips)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    job = job_store.create()
    background_tasks.add_task(
        run_compilation, job_store, job["id"], clips, body.output_4k, usage_store
    )
    return JSONResponse(status_code=202, content=_public(job).model_dump())


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


def _public(job: JobRecord) -> JobStatus:
    """The job fields the API returns. Working paths stay on the server."""
    download_url = None
    if job["status"] == "ready" and job.get("output_path"):
        download_url = f"/api/compilations/{job['id']}/download"
    return JobStatus(
        id=job["id"],
        status=job["status"],
        progress=job["progress"],
        error=job.get("error"),
        download_url=download_url,
        saved_path=job.get("saved_path"),
    )
