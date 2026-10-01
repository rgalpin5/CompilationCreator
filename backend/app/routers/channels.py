from fastapi import APIRouter, Depends, HTTPException, Query

from app.config import DEFAULT_VIDEO_LIMIT, MAX_VIDEO_LIMIT
from app.models import ChannelRequest, ChannelResponse, VideoItem
from app.routers.deps import get_usage_store
from app.usage.store import UsageStore
from app.youtube.listing import list_channel_videos
from app.youtube.urls import ChannelError

router = APIRouter()


@router.post("/channels", response_model=ChannelResponse)
def read_channel(
    body: ChannelRequest,
    limit: int = Query(default=DEFAULT_VIDEO_LIMIT, ge=1, le=MAX_VIDEO_LIMIT),
    offset: int = Query(default=0, ge=0, le=100_000),
    usage: UsageStore = Depends(get_usage_store),
) -> ChannelResponse:
    """Return one page of videos for the channel in ``body``."""
    try:
        videos, has_more = list_channel_videos(body.url, limit, offset)
    except ChannelError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    counts = usage.counts_for([video["video_id"] for video in videos])
    for video in videos:
        video["compilation_count"] = counts.get(video["video_id"], 0)
    return ChannelResponse(
        videos=[VideoItem.model_validate(video) for video in videos],
        next_offset=offset + limit,
        has_more=has_more,
    )
