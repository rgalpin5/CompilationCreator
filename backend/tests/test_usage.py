import json
import tempfile
import unittest
from pathlib import Path

from app.services.usage_store import UsageStore


class UsageStoreTests(unittest.TestCase):
    def test_records_each_video_once_per_compilation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "usage.json"
            store = UsageStore(path)
            store.record(
                [
                    {"video_id": "abcdefghijk", "title": "One", "channel": "Dash", "view_count": 600000, "duration_seconds": 891},
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
