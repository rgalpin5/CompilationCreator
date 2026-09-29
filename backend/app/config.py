import os
from pathlib import Path

DEFAULT_VIDEO_LIMIT = 24
MAX_VIDEO_LIMIT = 50
# A mega compilation is 4–8 videos of about 20–30 minutes.
# 35 minutes leaves room for a video that runs slightly past 30:00.
MAX_CLIPS = 8
MAX_CLIP_SECONDS = 35 * 60
MAX_TOTAL_SECONDS = MAX_CLIPS * MAX_CLIP_SECONDS


class Settings:
    def __init__(self) -> None:
        root = Path(__file__).resolve().parents[1]
        jobs = os.environ.get("JOBS_DIR", str(root / "data" / "jobs"))
        self.jobs_dir = Path(jobs)
        origins = os.environ.get("CORS_ORIGINS", "http://localhost:3000")
        self.cors_origins = [item.strip() for item in origins.split(",") if item.strip()]


settings = Settings()
