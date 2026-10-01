import unittest
from unittest.mock import patch

import yt_dlp

from app.errors import ConfigurationError
from app.youtube.listing import _thumbnail, list_channel_videos
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


def _ydl_returning(info: object = None, error: BaseException | None = None) -> type:
    class _OneShotYDL(_FakeYDL):
        def extract_info(self, url: str, download: bool = False) -> dict:
            if error is not None:
                raise error
            return info  # type: ignore[return-value]

    return _OneShotYDL


class ListChannelEdgeTests(unittest.TestCase):
    def _list(self, ydl: type, offset: int = 0) -> tuple[list, bool]:
        with patch("app.youtube.listing.yt_dlp.YoutubeDL", ydl):
            return list_channel_videos(_CHANNEL, 5, offset)

    def test_limit_and_offset_are_checked_first(self) -> None:
        with self.assertRaises(ChannelError):
            list_channel_videos(_CHANNEL, 0)
        with self.assertRaises(ChannelError):
            list_channel_videos(_CHANNEL, 5, -1)

    def test_bad_url_is_a_channel_error(self) -> None:
        with self.assertRaises(ChannelError):
            list_channel_videos("https://example.com/not-youtube", 5)

    def test_configuration_error_is_reported_as_channel_error(self) -> None:
        ydl = _ydl_returning(error=ConfigurationError("Cookie file is missing."))
        with self.assertRaises(ChannelError) as caught:
            self._list(ydl)
        self.assertEqual(str(caught.exception), "Cookie file is missing.")

    def test_ytdlp_error_is_explained(self) -> None:
        ydl = _ydl_returning(error=yt_dlp.utils.DownloadError("HTTP 404"))
        with self.assertRaises(ChannelError) as caught:
            self._list(ydl)
        self.assertIn("Could not read that channel", str(caught.exception))

    def test_os_error_becomes_one_sentence(self) -> None:
        ydl = _ydl_returning(error=PermissionError(13, "Permission denied", "/tmp/c.txt"))
        with self.assertRaises(ChannelError) as caught:
            self._list(ydl)
        self.assertEqual(str(caught.exception), "Permission denied for /tmp/c.txt.")

    def test_no_info_on_the_first_page_is_an_error(self) -> None:
        with self.assertRaises(ChannelError):
            self._list(_ydl_returning(None))

    def test_no_info_on_a_later_page_ends_the_list(self) -> None:
        self.assertEqual(self._list(_ydl_returning(None), offset=5), ([], False))

    def test_entries_are_filtered_and_filled_in(self) -> None:
        info = {
            "uploader": "Uploader name",
            "entries": [
                None,
                {"id": "short"},
                {"id": "playlist001", "_type": "playlist"},
                {
                    "id": "abcdefghijk",
                    "url": "abcdefghijk",
                    "duration": "n/a",
                    "view_count": 12.0,
                    "thumbnails": [{"url": "small"}, {"url": "https://i.ytimg.com/big.jpg"}],
                },
                {"id": "bcdefghijkl", "thumbnails": [{"url": ""}], "channel": 7},
            ],
        }
        videos, has_more = self._list(_ydl_returning(info))
        # Four non-empty entries for a page of five: nothing further to fetch.
        self.assertFalse(has_more)
        self.assertEqual([v["video_id"] for v in videos], ["abcdefghijk", "bcdefghijkl"])
        first, second = videos
        self.assertEqual(first["title"], "Untitled")
        self.assertEqual(first["url"], "https://www.youtube.com/watch?v=abcdefghijk")
        self.assertIsNone(first["duration_seconds"])
        self.assertEqual(first["view_count"], 12)
        self.assertEqual(first["thumbnail"], "https://i.ytimg.com/big.jpg")
        self.assertEqual(first["channel"], "Uploader name")
        self.assertEqual(second["thumbnail"], "https://i.ytimg.com/vi/bcdefghijkl/hqdefault.jpg")
        self.assertIsNone(second["channel"])

    def test_only_unusable_entries_on_a_later_page_end_the_list(self) -> None:
        info = {"entries": [{"id": "short"}]}
        self.assertEqual(self._list(_ydl_returning(info), offset=5), ([], False))

    def test_thumbnail_needs_a_full_video_id(self) -> None:
        self.assertIsNone(_thumbnail({}, "short"))


if __name__ == "__main__":
    unittest.main()
