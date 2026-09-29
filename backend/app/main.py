from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routers import channels, compilations, usage
from app.services.job_store import JobStore
from app.services.usage_store import UsageStore

app = FastAPI(title="CompCreator")
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
usage_store = UsageStore(settings.jobs_dir.parent / "usage.json")
channels.init_usage(usage_store)
usage.init_usage(usage_store)
compilations.init_store(JobStore(settings.jobs_dir), usage_store)


@app.get("/health")
def health() -> dict:
    return {"ok": True}
