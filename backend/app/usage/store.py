"""Finished compilations, and how often each video was included."""

import json
import os
import threading
from datetime import datetime
from pathlib import Path
from typing import cast

from app.errors import ConfigurationError, ensure_directory
from app.records import CompilationEntry, UsageClip, UsageLogs, UsageVideo


class UsageStore:
    """Finished compilations, and how often each video was included."""

    def __init__(self, path: Path) -> None:
        """Load ``path``, creating its folder when the log does not exist yet.

        A log that cannot be read, or that is not JSON this process understands,
        raises ``ConfigurationError`` instead of being replaced with an empty log.
        """
        self.path = path
        ensure_directory(self.path.parent, purpose="usage folder")
        self._lock = threading.Lock()
        self._videos, self._compilations = self._load()

    def _load(self) -> tuple[dict[str, UsageVideo], list[CompilationEntry]]:
        if not self.path.exists():
            return {}, []
        if not self.path.is_file():
            raise ConfigurationError(f"{self.path} is not a file.")
        try:
            text = self.path.read_text(encoding="utf-8")
        except PermissionError as exc:
            raise ConfigurationError(f"Permission denied reading {self.path}.") from exc
        except UnicodeDecodeError as exc:
            raise ConfigurationError(f"{self.path} is not valid UTF-8.") from exc
        except OSError as exc:
            detail = exc.strerror or "the operating system rejected the request"
            raise ConfigurationError(f"Could not read {self.path}: {detail}.") from exc
        try:
            data: object = json.loads(text)
        except json.JSONDecodeError as exc:
            raise ConfigurationError(
                f"{self.path} is not valid JSON. Rename the file and start CompCreator again."
            ) from exc
        if not isinstance(data, dict):
            raise ConfigurationError(
                f"{self.path} has an unexpected format. "
                "Rename the file and start CompCreator again."
            )
        if data and all(isinstance(value, int) for value in data.values()):
            videos = {
                video_id: _blank_video(video_id, count)
                for video_id, count in data.items()
                if isinstance(video_id, str) and isinstance(count, int) and count > 0
            }
            return videos, []
        raw_videos = data.get("videos")
        loaded_videos = raw_videos if isinstance(raw_videos, dict) else {}
        raw_compilations = data.get("compilations")
        compilations = raw_compilations if isinstance(raw_compilations, list) else []
        clean_videos = {
            video_id: cast(UsageVideo, entry)
            for video_id, entry in loaded_videos.items()
            if isinstance(video_id, str) and isinstance(entry, dict)
        }
        clean_compilations = [
            cast(CompilationEntry, entry) for entry in compilations if isinstance(entry, dict)
        ]
        return clean_videos, clean_compilations

    def count(self, video_id: str) -> int:
        """How many finished compilations include ``video_id``."""
        with self._lock:
            entry = self._videos.get(video_id)
            return int(entry["count"]) if entry else 0

    def counts_for(self, video_ids: list[str]) -> dict[str, int]:
        """Compilation counts for ``video_ids``, using 0 when a video is new."""
        with self._lock:
            return {
                video_id: int(self._videos[video_id]["count"]) if video_id in self._videos else 0
                for video_id in video_ids
            }

    def record(self, clips: list[UsageClip], duration_seconds: int = 0) -> str | None:
        """Count each video once for this compilation, even if it appears twice."""
        unique: list[UsageClip] = []
        seen: set[str] = set()
        for clip in clips:
            video_id = clip.get("video_id")
            if not isinstance(video_id, str) or video_id in seen:
                continue
            seen.add(video_id)
            unique.append(clip)
        if not unique:
            return None

        now = datetime.now().astimezone()
        stamp = now.isoformat(timespec="seconds")
        with self._lock:
            for clip in unique:
                video_id = clip.get("video_id")
                if not isinstance(video_id, str):
                    continue
                current = self._videos.get(video_id) or _blank_video(video_id, 0)
                current["count"] = int(current.get("count") or 0) + 1
                current["last_used"] = stamp
                title = clip.get("title")
                if isinstance(title, str) and title.strip():
                    current["title"] = title.strip()[:500]
                channel = clip.get("channel")
                if isinstance(channel, str) and channel.strip():
                    current["channel"] = channel.strip()[:500]
                thumbnail = clip.get("thumbnail")
                if isinstance(thumbnail, str) and thumbnail.strip():
                    current["thumbnail"] = thumbnail.strip()[:500]
                view_count = clip.get("view_count")
                if isinstance(view_count, int) and view_count >= 0:
                    current["view_count"] = view_count
                clip_duration = clip.get("duration_seconds")
                if isinstance(clip_duration, int) and clip_duration >= 0:
                    current["duration_seconds"] = clip_duration
                self._videos[video_id] = current

            name = _compilation_name(now, self._compilations)
            self._compilations.insert(
                0,
                {
                    "name": name,
                    "made": stamp,
                    "clips": len(unique),
                    "duration_seconds": max(0, int(duration_seconds)),
                },
            )
            self._compilations = self._compilations[:200]
            self._save()
            return name

    def logs(self) -> UsageLogs:
        """Copies of the video rows and compilation rows, newest compilation first."""
        with self._lock:
            videos = [entry.copy() for entry in self._videos.values()]
            compilations = [entry.copy() for entry in self._compilations]
        return {"videos": videos, "compilations": compilations}

    def _save(self) -> None:
        payload = {"videos": self._videos, "compilations": self._compilations}
        # Write beside the log and swap it in, so a crash mid-write leaves the
        # previous log intact instead of a truncated file that blocks startup.
        partial = self.path.with_name(f".{self.path.name}.{os.getpid()}.partial")
        try:
            partial.write_text(json.dumps(payload, indent=2), encoding="utf-8")
            os.replace(partial, self.path)
        except OSError:
            partial.unlink(missing_ok=True)
            raise


def _blank_video(video_id: str, count: int) -> UsageVideo:
    return {
        "video_id": video_id,
        "title": video_id,
        "channel": None,
        "view_count": None,
        "duration_seconds": None,
        "thumbnail": None,
        "last_used": None,
        "count": count,
    }


def _compilation_name(now: datetime, compilations: list[CompilationEntry]) -> str:
    base = f"{now.day} {now.strftime('%b')}, {now.strftime('%H:%M')}"
    name = f"{base}.mp4"
    taken = {entry.get("name") for entry in compilations}
    if name not in taken:
        return name
    return f"{base}:{now.strftime('%S')}.mp4"
