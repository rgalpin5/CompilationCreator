import unittest
from unittest.mock import patch

from app.youtube.listing import list_channel_videos
from app.youtube.urls import ChannelError

_CHANNEL = "https://www.youtube.com/@somechannel"


def _entry(number: int) -> dict:
    video_id = f"{number:011d}"
    return {
        "id": video_id,
        "title": f"Video {number}",
        "duration": 60,
        "view_count": number,
        "url": f"https://www.youtube.com/watch?v={video_id}",
    }


class _FakeYDL:
    catalog_size = 30

    def __init__(self, options: dict) -> None:
        self.options = options

    def __enter__(self) -> "_FakeYDL":
        return self

    def __exit__(self, _exc_type: object, _exc: object, _tb: object) -> None:
        return None

    def extract_info(self, url: str, download: bool = False) -> dict:
        start_s, end_s = self.options["playlist_items"].split(":")
        start, end = int(start_s), int(end_s)
        catalog = [_entry(i) for i in range(1, self.catalog_size + 1)]
        return {
            "channel": "Some channel",
            "entries": catalog[start - 1 : end],
        }


class ListChannelVideosTests(unittest.TestCase):
    def test_first_page_reports_another_page(self) -> None:
        with patch("app.youtube.listing.yt_dlp.YoutubeDL", _FakeYDL):
            videos, has_more = list_channel_videos(_CHANNEL, 24, 0)

        self.assertEqual(len(videos), 24)
        self.assertEqual(videos[0]["video_id"], f"{1:011d}")
        self.assertEqual(videos[-1]["video_id"], f"{24:011d}")
        self.assertTrue(has_more)

    def test_later_page_stops_at_the_end(self) -> None:
        with patch("app.youtube.listing.yt_dlp.YoutubeDL", _FakeYDL):
            videos, has_more = list_channel_videos(_CHANNEL, 24, 24)

        self.assertEqual(
            [video["video_id"] for video in videos],
            [f"{i:011d}" for i in range(25, 31)],
        )
        self.assertFalse(has_more)

    def test_offset_past_the_end_is_an_empty_page(self) -> None:
        with patch("app.youtube.listing.yt_dlp.YoutubeDL", _FakeYDL):
            videos, has_more = list_channel_videos(_CHANNEL, 24, 48)

        self.assertEqual(videos, [])
        self.assertFalse(has_more)

    def test_empty_channel_on_the_first_page_is_an_error(self) -> None:
        class EmptyYDL(_FakeYDL):
            catalog_size = 0

        with (
            patch("app.youtube.listing.yt_dlp.YoutubeDL", EmptyYDL),
            self.assertRaises(ChannelError),
        ):
            list_channel_videos(_CHANNEL, 24, 0)


if __name__ == "__main__":
    unittest.main()
