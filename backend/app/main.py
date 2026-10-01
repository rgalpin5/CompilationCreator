from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.auth import PasswordMiddleware, hide_tokens_in_access_log, require_password_when_hosted
from app.config import settings
from app.errors import ConfigurationError, stop_for_local_error, terminal_message
from app.jobs.store import JobStore
from app.local_host import LocalHostMiddleware
from app.models import Ok, error_responses
from app.routers import channels, compilations, usage
from app.usage.store import UsageStore


@asynccontextmanager
async def _lifespan(application: FastAPI) -> AsyncIterator[None]:
    """Open the usage log and the jobs folder for this process.

    A hosted server without a password, a folder that cannot be created, or a
    usage log that cannot be read prints one line and stops the process.
    """
    # After uvicorn has configured logging, so the filter is not reset.
    hide_tokens_in_access_log()
    try:
        require_password_when_hosted()
        application.state.usage_store = UsageStore(settings.jobs_dir.parent / "usage.json")
        application.state.job_store = JobStore(settings.jobs_dir)
    except (ConfigurationError, OSError) as exc:
        stop_for_local_error(exc)
    yield


# A hosted server's password guards /api only, so it does not publish its docs.
# The schema is still generated from ``app.openapi()`` for the frontend types.
app = FastAPI(
    title="CompCreator",
    lifespan=_lifespan,
    docs_url=None if settings.hosted else "/docs",
    redoc_url=None if settings.hosted else "/redoc",
    openapi_url=None if settings.hosted else "/openapi.json",
)
# Middleware added later wraps earlier middleware, so CORS stays outermost.
app.add_middleware(LocalHostMiddleware)
app.add_middleware(PasswordMiddleware)
# The password travels in the Authorization header, not a cookie, so the
# browser never needs to send credentials across origins.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=False,
    allow_methods=["GET", "HEAD", "POST"],
    allow_headers=["Authorization", "Content-Type"],
)
# PasswordMiddleware can answer any /api route with these when a password is set.
_password_errors = error_responses(401, 429)
app.include_router(channels.router, prefix="/api", responses=_password_errors)
app.include_router(compilations.router, prefix="/api", responses=_password_errors)
app.include_router(usage.router, prefix="/api", responses=_password_errors)


@app.exception_handler(ConfigurationError)
async def configuration_error(_request: Request, exc: ConfigurationError) -> JSONResponse:
    """Return the configuration sentence instead of a server traceback."""
    return JSONResponse(status_code=500, content={"detail": terminal_message(exc)})


@app.exception_handler(PermissionError)
async def permission_error(_request: Request, exc: PermissionError) -> JSONResponse:
    """Return a permission sentence instead of a server traceback."""
    return JSONResponse(status_code=500, content={"detail": _file_message(exc)})


@app.exception_handler(FileNotFoundError)
async def missing_file(_request: Request, exc: FileNotFoundError) -> JSONResponse:
    """Return a missing-file sentence instead of a server traceback."""
    return JSONResponse(status_code=404, content={"detail": _file_message(exc)})


def _file_message(exc: OSError) -> str:
    """``terminal_message``, naming only the file rather than its server path when hosted."""
    message = terminal_message(exc)
    if settings.hosted and isinstance(exc.filename, str) and exc.filename:
        message = message.replace(exc.filename, Path(exc.filename).name)
    return message


@app.get("/health", response_model=Ok)
def health() -> Ok:
    """Report that the API process is accepting requests."""
    return Ok(ok=True)


@app.get("/api/session", response_model=Ok, responses=_password_errors)
def session() -> Ok:
    """Answer 200 when the request may use the API, so the UI can ask for a password first."""
    return Ok(ok=True)
