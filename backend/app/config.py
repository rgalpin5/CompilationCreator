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


def _trusted_proxy_hops() -> int:
    """``COMPCREATOR_TRUSTED_PROXY_HOPS`` as a whole number of at least 1. Defaults to 1."""
    raw = os.environ.get("COMPCREATOR_TRUSTED_PROXY_HOPS", "").strip()
    if not raw:
        return 1
    try:
        hops = int(raw)
    except ValueError:
        hops = 0
    if hops < 1:
        raise ConfigurationError(
            f"COMPCREATOR_TRUSTED_PROXY_HOPS must be a whole number of at least 1, not {raw!r}."
        )
    return hops


class Settings:
    """Paths and origins read once from the environment."""

    def __init__(self) -> None:
        """Read ``JOBS_DIR``, ``CORS_ORIGINS``, ``VERCEL`` and friends, using local defaults."""
        jobs = os.environ.get("JOBS_DIR")
        self.jobs_dir = Path(jobs) if jobs else _default_jobs_dir()
        # A hosted deploy serves anyone who can reach it, so the caller must
        # not choose where on the server a file is written. The finished video
        # goes to the browser instead. Vercel sets VERCEL; Cloud Run sets K_SERVICE.
        self.hosted = bool(os.environ.get("VERCEL") or os.environ.get("K_SERVICE"))
        # Required on a hosted server; see app/auth.py.
        self.password = os.environ.get("COMPCREATOR_PASSWORD") or None
        # Proxies in front of a hosted server that each append to X-Forwarded-For.
        # Cloud Run's own URL adds one; a load balancer or CDN in front adds more.
        self.trusted_proxy_hops = _trusted_proxy_hops()
        origins = os.environ.get("CORS_ORIGINS", "http://localhost:3000")
        self.cors_origins = [item.strip() for item in origins.split(",") if item.strip()]


try:
    settings = Settings()
except ConfigurationError as exc:
    stop_for_local_error(exc)
