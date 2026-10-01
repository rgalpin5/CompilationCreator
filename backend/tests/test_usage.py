import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from app.usage.store import UsageStore


class UsageStoreTests(unittest.TestCase):
    def test_records_each_video_once_per_compilation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "usage.json"
            store = UsageStore(path)
            store.record(
                [
                    {
                        "video_id": "abcdefghijk",
                        "title": "One",
                        "channel": "Dash",
                        "view_count": 600000,
                        "duration_seconds": 891,
                    },
                    {"video_id": "abcdefghijk", "title": "One"},
                    {"video_id": "abcdefghijl", "title": "Two"},
                ],
                duration_seconds=1200,
            )
            self.assertEqual(store.count("abcdefghijk"), 1)
            self.assertEqual(store.count("abcdefghijl"), 1)
            logs = store.logs()
            self.assertEqual(len(logs["compilations"]), 1)
            self.assertEqual(logs["compilations"][0]["clips"], 2)
            self.assertEqual(logs["compilations"][0]["duration_seconds"], 1200)
            saved = {video["video_id"]: video for video in logs["videos"]}
            self.assertEqual(saved["abcdefghijk"]["channel"], "Dash")
            self.assertEqual(saved["abcdefghijk"]["view_count"], 600000)

            reloaded = UsageStore(path)
            reloaded.record([{"video_id": "abcdefghijk", "title": "One"}])
            self.assertEqual(reloaded.count("abcdefghijk"), 2)
            self.assertEqual(len(reloaded.logs()["compilations"]), 2)

    def test_migrates_old_counts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "usage.json"
            path.write_text(json.dumps({"abcdefghijk": 3}))
            store = UsageStore(path)
            self.assertEqual(store.count("abcdefghijk"), 3)
            videos = store.logs()["videos"]
            self.assertEqual(videos[0]["title"], "abcdefghijk")
            self.assertEqual(videos[0]["last_used"], None)

    def test_malformed_entries_are_dropped_on_load(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "usage.json"
            path.write_text(
                json.dumps(
                    {
                        "videos": {
                            "abcdefghijk": {"video_id": "abcdefghijk", "title": "Kept", "count": 2},
                            "nocount0000": {"video_id": "nocount0000", "title": "No count"},
                            "textcount00": {"title": "Text", "count": "3"},
                            "boolcount00": {"title": "Bool", "count": True},
                            "badfields00": {"count": 1, "title": 5, "view_count": "many"},
                            "notadict000": 7,
                        },
                        "compilations": [
                            {
                                "name": "a.mp4",
                                "made": "2026-01-01T00:00:00+00:00",
                                "clips": 2,
                                "duration_seconds": 60,
                            },
                            {"name": "b.mp4", "made": "2026-01-01T00:00:00+00:00"},
                            {"name": "c.mp4", "made": "now", "clips": "2", "duration_seconds": 1},
                            "not a dict",
                        ],
                    }
                ),
                encoding="utf-8",
            )
            store = UsageStore(path)

            self.assertEqual(
                store.counts_for(["abcdefghijk", "nocount0000", "textcount00", "boolcount00"]),
                {"abcdefghijk": 2, "nocount0000": 0, "textcount00": 0, "boolcount00": 0},
            )
            self.assertEqual(store.count("badfields00"), 1)
            videos = {video["video_id"]: video for video in store.logs()["videos"]}
            self.assertEqual(set(videos), {"abcdefghijk", "badfields00"})
            self.assertEqual(videos["badfields00"]["title"], "badfields00")
            self.assertIsNone(videos["badfields00"]["view_count"])
            names = [entry["name"] for entry in store.logs()["compilations"]]
            self.assertEqual(names, ["a.mp4"])

            store.record([{"video_id": "nocount0000", "title": "No count"}])
            self.assertEqual(store.count("nocount0000"), 1)

    def test_failed_save_keeps_the_previous_log(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "usage.json"
            store = UsageStore(path)
            store.record([{"video_id": "abcdefghijk", "title": "One"}])
            before = path.read_text(encoding="utf-8")

            with (
                patch("app.usage.store.os.replace", side_effect=OSError("disk full")),
                self.assertRaises(OSError),
            ):
                store.record([{"video_id": "abcdefghijl", "title": "Two"}])

            self.assertEqual(path.read_text(encoding="utf-8"), before)
            self.assertEqual([item.name for item in Path(tmp).iterdir()], ["usage.json"])
            self.assertEqual(UsageStore(path).count("abcdefghijk"), 1)
