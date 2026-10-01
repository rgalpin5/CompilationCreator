"""Structured records shared by jobs, usage, and channel listing."""

from __future__ import annotations

from typing import Literal, NotRequired, TypedDict

JobState = Literal[
    "queued", "downloading", "concatenating", "ready", "saved", "failed", "cancelled"
]


class JobRecord(TypedDict):
    """One export, as stored for the life of the API process."""

    id: str
    status: JobState
    progress: str
    error: str | None
    dir: str
    output_path: str | None
    filename: NotRequired[str | None]
    saved_path: NotRequired[str | None]


class JobUpdate(TypedDict, total=False):
    """Fields ``JobStore.update`` accepts. Omitted keys stay as they are."""

    status: JobState
    progress: str
    error: str | None
    dir: str
    output_path: str | None
    filename: str | None
    saved_path: str | None


class ListedVideo(TypedDict):
    """One channel video returned before compilation counts are attached."""

    video_id: str
    title: str
    thumbnail: str | None
    duration_seconds: int | None
    url: str
    channel: str | None
    view_count: int | None
    compilation_count: NotRequired[int]


class UsageClip(TypedDict, total=False):
    """A clip handed to the usage log when an export finishes."""

    video_id: str
    title: str
    channel: str | None
    view_count: int | None
    duration_seconds: int | None
    thumbnail: str | None


class UsageVideo(TypedDict):
    """How often one video has been included, plus the last title seen."""

    video_id: str
    title: str
    channel: str | None
    view_count: int | None
    duration_seconds: int | None
    thumbnail: str | None
    last_used: str | None
    count: int


class CompilationEntry(TypedDict):
    """One finished compilation in the usage log."""

    name: str
    made: str
    clips: int
    duration_seconds: int


class UsageLogs(TypedDict):
    """The two tables shown on the Logs screen."""

    videos: list[UsageVideo]
    compilations: list[CompilationEntry]
