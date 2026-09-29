import re

from fastapi import APIRouter, Query

from app.services.usage_store import UsageStore

_VIDEO_ID = re.compile(r"^[A-Za-z0-9_-]{11}$")

router = APIRouter()
usage: UsageStore | None = None


def init_usage(store: UsageStore) -> None:
    global usage
    usage = store


@router.get("/usage")
def read_usage(ids: str = Query(default="")) -> dict:
    wanted = [part for part in ids.split(",") if _VIDEO_ID.fullmatch(part)][:50]
    counts = usage.counts_for(wanted) if usage else {video_id: 0 for video_id in wanted}
    return {"counts": counts}


@router.get("/logs")
def read_logs() -> dict:
    if usage is None:
        return {"videos": [], "compilations": []}
    return usage.logs()
