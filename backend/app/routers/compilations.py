import shutil

from fastapi import APIRouter, BackgroundTasks, HTTPException
from fastapi.responses import FileResponse, JSONResponse

from app.models import CompilationRequest, JobStatus
from app.services.compiler import run_compilation, validate_timeline
from app.services.job_store import JobStore
from app.services.runner import runner
from app.services.usage_store import UsageStore

_ACTIVE = {"queued", "downloading", "concatenating"}

router = APIRouter()
store: JobStore | None = None
usage: UsageStore | None = None


def init_store(job_store: JobStore, usage_store: UsageStore | None = None) -> None:
    global store, usage
    store = job_store
    usage = usage_store


def _require_store() -> JobStore:
    if store is None:
        raise HTTPException(status_code=500, detail="Job store is not ready")
    return store


@router.post("/compilations", status_code=202)
def create_compilation(body: CompilationRequest, background_tasks: BackgroundTasks) -> JSONResponse:
    try:
        clips = validate_timeline(body.clips)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    job_store = _require_store()
    job = job_store.create()
    background_tasks.add_task(
        run_compilation, job_store, job["id"], clips, body.output_4k, usage
    )
    return JSONResponse(status_code=202, content=_public(job))


@router.get("/compilations/{job_id}", response_model=JobStatus)
def compilation_status(job_id: str) -> JobStatus:
    job = _require_store().get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return JobStatus(**_public(job))


@router.post("/compilations/{job_id}/cancel", response_model=JobStatus)
def cancel_compilation(job_id: str) -> JobStatus:
    job_store = _require_store()
    job = job_store.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job["status"] not in _ACTIVE:
        raise HTTPException(status_code=409, detail="That export is no longer running")
    job_store.update(job_id, status="cancelled", progress="Cancelled", error=None, output_path=None)
    runner.cancel(job_id)
    shutil.rmtree(job["dir"], ignore_errors=True)
    cancelled = job_store.get(job_id)
    if not cancelled:
        raise HTTPException(status_code=404, detail="Job not found")
    return JobStatus(**_public(cancelled))


@router.get("/compilations/{job_id}/download")
def download_compilation(job_id: str) -> FileResponse:
    job = _require_store().get(job_id)
    if not job or job["status"] != "ready" or not job.get("output_path"):
        raise HTTPException(status_code=404, detail="Compilation is not ready")
    # Later Cloud Run deploy: upload output_path to GCS and return a signed URL
    # instead of streaming from the instance disk. See app/stubs/gcs_download.py.
    return FileResponse(
        job["output_path"],
        media_type="video/mp4",
        filename="compilation.mp4",
    )


def _public(job: dict) -> dict:
    download_url = None
    if job["status"] == "ready":
        download_url = f"/api/compilations/{job['id']}/download"
    return {
        "id": job["id"],
        "status": job["status"],
        "progress": job["progress"],
        "error": job.get("error"),
        "download_url": download_url,
    }
