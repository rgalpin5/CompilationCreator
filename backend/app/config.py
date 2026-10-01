import os
from pathlib import Path

from app.envfile import load_env_file
from app.errors import ConfigurationError, stop_for_local_error

DEFAULT_VIDEO_LIMIT = 24
MAX_VIDEO_LIMIT = 50

# backend/app/config.py -> repository root. Hosted deploys usually have no
# file here, and values already present in the environment are left alone.
try:
    load_env_file(Path(__file__).resolve().parents[2] / ".env", os.environ)
except ConfigurationError as exc:
    stop_for_local_error(exc)


def _default_jobs_dir() -> Path:
    """Jobs folder for this process: ``JOBS_DIR``, or a writable default."""
    # Vercel bundles the app on a read-only filesystem. /tmp is writable.
    if os.environ.get("VERCEL"):
        return Path("/tmp/compcreator/jobs")
    root = Path(__file__).resolve().parents[1]
    return root / "data" / "jobs"


class Settings:
    """Paths and origins read once from the environment."""

    def __init__(self) -> None:
        """Read ``JOBS_DIR``, ``CORS_ORIGINS``, and ``VERCEL``, using local defaults when unset."""
        jobs = os.environ.get("JOBS_DIR")
        self.jobs_dir = Path(jobs) if jobs else _default_jobs_dir()
        # A hosted deploy serves anyone who can reach it, so the caller must
        # not choose where on the server a file is written.
        self.hosted = bool(os.environ.get("VERCEL"))
        origins = os.environ.get("CORS_ORIGINS", "http://localhost:3000")
        self.cors_origins = [item.strip() for item in origins.split(",") if item.strip()]


settings = Settings()
