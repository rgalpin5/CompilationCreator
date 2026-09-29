import re

from pydantic import BaseModel, Field, field_validator

from app.config import MAX_CLIPS

_VIDEO_ID = re.compile(r"^[A-Za-z0-9_-]{11}$")


class ChannelRequest(BaseModel):
    url: str = Field(min_length=3, max_length=500)


class VideoItem(BaseModel):
    video_id: str
    title: str
    thumbnail: str | None = None
    duration_seconds: int | None = None
    url: str
    compilation_count: int = 0
    channel: str | None = None
    view_count: int | None = None


class ChannelResponse(BaseModel):
    videos: list[VideoItem]


class Clip(BaseModel):
    video_id: str
    title: str = "Untitled"
    start: str
    end: str
    order: int = 0
    channel: str | None = None
    view_count: int | None = Field(default=None, ge=0)
    duration_seconds: int | None = Field(default=None, ge=0)
    thumbnail: str | None = None

    @field_validator("video_id")
    @classmethod
    def video_id_shape(cls, value: str) -> str:
        if not _VIDEO_ID.fullmatch(value):
            raise ValueError("video_id must be an 11-character YouTube id")
        return value

    @field_validator("title")
    @classmethod
    def title_length(cls, value: str) -> str:
        text = value.strip() or "Untitled"
        return text[:200]


class CompilationRequest(BaseModel):
    clips: list[Clip] = Field(min_length=1, max_length=MAX_CLIPS)
    output_4k: bool = False


class JobStatus(BaseModel):
    id: str
    status: str
    progress: str
    error: str | None = None
    download_url: str | None = None
