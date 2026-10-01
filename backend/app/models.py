import re

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.records import JobState

_VIDEO_ID = re.compile(r"^[A-Za-z0-9_-]{11}$")
# Hard limits that stop an oversized body before any work is done. They sit
# well above real values; validate.py applies the readable limits afterwards.
_MAX_REQUEST_CLIPS = 1000
_MAX_TEXT = 1000
_MAX_URL = 2000


class _Response(BaseModel):
    """A response body. Every field is always sent, so the schema marks them all required."""

    model_config = ConfigDict(json_schema_serialization_defaults_required=True)


class ChannelRequest(BaseModel):
    url: str = Field(min_length=3, max_length=500)


class VideoItem(_Response):
    video_id: str
    title: str
    thumbnail: str | None = None
    duration_seconds: int | None = None
    url: str
    compilation_count: int = 0
    channel: str | None = None
    view_count: int | None = None


class ChannelResponse(_Response):
    videos: list[VideoItem]
    next_offset: int = 0
    has_more: bool = False


class Clip(BaseModel):
    video_id: str
    title: str = Field(default="Untitled", max_length=_MAX_TEXT)
    start: str = Field(max_length=20)
    end: str = Field(max_length=20)
    order: int = 0
    channel: str | None = Field(default=None, max_length=_MAX_TEXT)
    view_count: int | None = Field(default=None, ge=0)
    duration_seconds: int | None = Field(default=None, ge=0)
    thumbnail: str | None = Field(default=None, max_length=_MAX_URL)

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
    clips: list[Clip] = Field(min_length=1, max_length=_MAX_REQUEST_CLIPS)
    output_4k: bool = False


class DownloadRequest(BaseModel):
    directory: str | None = None


class JobStatus(_Response):
    id: str
    status: JobState
    progress: str
    error: str | None = None
    download_url: str | None = None
    file_url: str | None = None
    saved_path: str | None = None


class ErrorDetail(_Response):
    """The body of every error the API raises itself: one sentence a person can read."""

    detail: str


class DownloadFolder(_Response):
    path: str


class UsageCounts(_Response):
    counts: dict[str, int]


class Ok(_Response):
    ok: bool


_ERROR_DESCRIPTIONS = {
    400: "The request is invalid",
    401: "The server's password is missing or wrong",
    404: "No such job, or its file is not ready",
    409: "The job is in the wrong state for this request",
    429: "Too many wrong passwords from this client",
    500: "The server could not finish the request",
}


def error_responses(*codes: int) -> dict[int | str, dict[str, object]]:
    """OpenAPI entries for the ``ErrorDetail`` responses a route can return."""
    return {
        code: {"model": ErrorDetail, "description": _ERROR_DESCRIPTIONS[code]} for code in codes
    }
