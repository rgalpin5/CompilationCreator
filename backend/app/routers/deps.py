"""Job and usage stores stored on the running app."""

from fastapi import HTTPException, Request

from app.jobs.store import JobStore
from app.usage.store import UsageStore


def get_job_store(request: Request) -> JobStore:
    """The job store opened when this process started."""
    store = getattr(request.app.state, "job_store", None)
    if not isinstance(store, JobStore):
        raise HTTPException(status_code=500, detail="Job store is not ready")
    return store


def get_usage_store(request: Request) -> UsageStore:
    """The usage log opened when this process started."""
    store = getattr(request.app.state, "usage_store", None)
    if not isinstance(store, UsageStore):
        raise HTTPException(status_code=500, detail="Usage store is not ready")
    return store
