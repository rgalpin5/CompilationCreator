import json
import threading
from datetime import datetime
from pathlib import Path


class UsageStore:
    """Finished compilations, and how often each video was included."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._videos, self._compilations = self._load()

    def _load(self) -> tuple[dict[str, dict], list[dict]]:
        if not self.path.exists():
            return {}, []
        try:
            data = json.loads(self.path.read_text())
        except (OSError, json.JSONDecodeError):
            return {}, []
        if not isinstance(data, dict):
            return {}, []
        if data and all(isinstance(value, int) for value in data.values()):
            videos = {
                video_id: _blank_video(video_id, count)
                for video_id, count in data.items()
                if isinstance(video_id, str) and isinstance(count, int) and count > 0
            }
            return videos, []
        videos = data.get("videos") if isinstance(data.get("videos"), dict) else {}
        compilations = data.get("compilations") if isinstance(data.get("compilations"), list) else []
        clean_videos = {
            video_id: entry
            for video_id, entry in videos.items()
            if isinstance(video_id, str) and isinstance(entry, dict)
        }
        clean_compilations = [entry for entry in compilations if isinstance(entry, dict)]
        return clean_videos, clean_compilations

    def count(self, video_id: str) -> int:
        with self._lock:
            entry = self._videos.get(video_id)
            return int(entry["count"]) if entry else 0

    def counts_for(self, video_ids: list[str]) -> dict[str, int]:
        with self._lock:
            return {
                video_id: int(self._videos[video_id]["count"]) if video_id in self._videos else 0
                for video_id in video_ids
            }

    def record(self, clips: list[dict], duration_seconds: int = 0) -> None:
        """Count each video once for this compilation, even if it appears twice."""
        unique: list[dict] = []
        seen: set[str] = set()
        for clip in clips:
            video_id = clip.get("video_id")
            if not isinstance(video_id, str) or video_id in seen:
                continue
            seen.add(video_id)
            unique.append(clip)
        if not unique:
            return

        now = datetime.now().astimezone()
        stamp = now.isoformat(timespec="seconds")
        with self._lock:
            for clip in unique:
                video_id = clip["video_id"]
                current = self._videos.get(video_id) or _blank_video(video_id, 0)
                current["count"] = int(current.get("count") or 0) + 1
                current["last_used"] = stamp
                for field in ("title", "channel", "thumbnail"):
                    value = clip.get(field)
                    if isinstance(value, str) and value.strip():
                        current[field] = value.strip()[:500]
                for field in ("view_count", "duration_seconds"):
                    value = clip.get(field)
                    if isinstance(value, int) and value >= 0:
                        current[field] = value
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

    def logs(self) -> dict:
        with self._lock:
            videos = [dict(entry) for entry in self._videos.values()]
            compilations = [dict(entry) for entry in self._compilations]
        return {"videos": videos, "compilations": compilations}

    def _save(self) -> None:
        payload = {"videos": self._videos, "compilations": self._compilations}
        self.path.write_text(json.dumps(payload, indent=2))


def _blank_video(video_id: str, count: int) -> dict:
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


def _compilation_name(now: datetime, compilations: list[dict]) -> str:
    base = f"{now.day} {now.strftime('%b')}, {now.strftime('%H:%M')}"
    name = f"{base}.mp4"
    taken = {entry.get("name") for entry in compilations}
    if name not in taken:
        return name
    return f"{base}:{now.strftime('%S')}.mp4"
