from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import settings
from app.errors import ConfigurationError, stop_for_local_error, terminal_message
from app.jobs.store import JobStore
from app.routers import channels, compilations, usage
from app.usage.store import UsageStore


@asynccontextmanager
async def _lifespan(application: FastAPI) -> AsyncIterator[None]:
    """Open the usage log and the jobs folder for this process.

    A folder that cannot be created, or a usage log that cannot be read,
    prints one line and stops the process. The server does not stay up
    without those files.
    """
    try:
        application.state.usage_store = UsageStore(settings.jobs_dir.parent / "usage.json")
        application.state.job_store = JobStore(settings.jobs_dir)
    except (ConfigurationError, OSError) as exc:
        stop_for_local_error(exc)
    yield


app = FastAPI(title="CompCreator", lifespan=_lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(channels.router, prefix="/api")
app.include_router(compilations.router, prefix="/api")
app.include_router(usage.router, prefix="/api")


@app.exception_handler(ConfigurationError)
async def configuration_error(_request: Request, exc: ConfigurationError) -> JSONResponse:
    """Return the configuration sentence instead of a server traceback."""
    return JSONResponse(status_code=500, content={"detail": terminal_message(exc)})


@app.exception_handler(PermissionError)
async def permission_error(_request: Request, exc: PermissionError) -> JSONResponse:
    """Return a permission sentence instead of a server traceback."""
    return JSONResponse(status_code=500, content={"detail": terminal_message(exc)})


@app.exception_handler(FileNotFoundError)
async def missing_file(_request: Request, exc: FileNotFoundError) -> JSONResponse:
    """Return a missing-file sentence instead of a server traceback."""
    return JSONResponse(status_code=404, content={"detail": terminal_message(exc)})


@app.get("/health")
def health() -> dict[str, bool]:
    """Report that the API process is accepting requests."""
    return {"ok": True}
