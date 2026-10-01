import re

from fastapi import APIRouter, Depends, Query

from app.models import UsageCounts
from app.records import UsageLogs
from app.routers.deps import get_usage_store
from app.usage.store import UsageStore

_VIDEO_ID = re.compile(r"^[A-Za-z0-9_-]{11}$")

router = APIRouter()


@router.get("/usage", response_model=UsageCounts)
def read_usage(
    ids: str = Query(default=""),
    usage: UsageStore = Depends(get_usage_store),
) -> UsageCounts:
    """Compilation counts for the comma-separated video ids in ``ids``."""
    wanted = [part for part in ids.split(",") if _VIDEO_ID.fullmatch(part)][:50]
    return UsageCounts(counts=usage.counts_for(wanted))


@router.get("/logs")
def read_logs(usage: UsageStore = Depends(get_usage_store)) -> UsageLogs:
    """Videos and compilations recorded on this computer."""
    return usage.logs()
