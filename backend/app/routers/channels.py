from fastapi import APIRouter, HTTPException, Query

from app.config import DEFAULT_VIDEO_LIMIT, MAX_VIDEO_LIMIT
from app.models import ChannelRequest, ChannelResponse
from app.services.usage_store import UsageStore
from app.services.ytdlp_service import ChannelError, list_channel_videos

router = APIRouter()
usage: UsageStore | None = None


def init_usage(store: UsageStore) -> None:
    global usage
    usage = store


@router.post("/channels", response_model=ChannelResponse)
def read_channel(
    body: ChannelRequest,
    limit: int = Query(default=DEFAULT_VIDEO_LIMIT, ge=1, le=MAX_VIDEO_LIMIT),
) -> ChannelResponse:
    try:
        videos = list_channel_videos(body.url, limit)
    except ChannelError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if usage:
        counts = usage.counts_for([video["video_id"] for video in videos])
        for video in videos:
            video["compilation_count"] = counts.get(video["video_id"], 0)
    return ChannelResponse(videos=videos)
