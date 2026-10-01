import unittest
from unittest.mock import patch

from app.compilation.validate import validate_timeline, videos_missing_4k
from app.models import Clip
from app.timeparse import format_timestamp, parse_timestamp
from app.youtube.urls import ChannelError, normalize_channel_url


class TimeParseTests(unittest.TestCase):
    def test_mm_ss(self) -> None:
        self.assertEqual(parse_timestamp("00:15"), 15)
        self.assertEqual(parse_timestamp("1:05"), 65)

    def test_hh_mm_ss(self) -> None:
        self.assertEqual(parse_timestamp("01:02:03"), 3723)

    def test_rejects_bad_clock(self) -> None:
        with self.assertRaises(ValueError):
            parse_timestamp("00:60")
        with self.assertRaises(ValueError):
            parse_timestamp("15")
        with self.assertRaises(ValueError):
            parse_timestamp("1:2:3")

    def test_format_mm_ss_and_hours(self) -> None:
        self.assertEqual(format_timestamp(0), "00:00")
        self.assertEqual(format_timestamp(15), "00:15")
        self.assertEqual(format_timestamp(65.9), "01:05")
        self.assertEqual(format_timestamp(3723), "1:02:03")

    def test_format_round_trips_through_parse(self) -> None:
        self.assertEqual(parse_timestamp(format_timestamp(3723)), 3723)
        self.assertEqual(parse_timestamp(format_timestamp(65)), 65)


class TimelineTests(unittest.TestCase):
    def test_orders_and_rejects_backwards_range(self) -> None:
        clips = [
            Clip(video_id="abcdefghijk", title="B", start="00:10", end="00:20", order=1),
            Clip(video_id="abcdefghijl", title="A", start="00:00", end="00:05", order=0),
        ]
        ordered = validate_timeline(clips)
        self.assertEqual([clip.title for clip in ordered], ["A", "B"])

        bad = [Clip(video_id="abcdefghijk", title="Bad", start="00:20", end="00:10", order=0)]
        with self.assertRaises(ValueError):
            validate_timeline(bad)

    def test_allows_thirty_minute_clip(self) -> None:
        clip = Clip(video_id="abcdefghijk", title="Episode", start="00:00", end="30:00", order=0)
        self.assertEqual(validate_timeline([clip])[0].title, "Episode")

    def test_allows_clip_over_thirty_five_minutes(self) -> None:
        clip = Clip(video_id="abcdefghijk", title="Long", start="00:00", end="1:10:00", order=0)
        self.assertEqual(validate_timeline([clip])[0].title, "Long")


class FourKTests(unittest.TestCase):
    def test_names_videos_below_2160(self) -> None:
        missing = videos_missing_4k([("A", 2160), ("B", 1080), ("C", None)])
        self.assertEqual(missing, ["B", "C"])

    def test_all_4k_is_empty(self) -> None:
        self.assertEqual(videos_missing_4k([("A", 2160), ("B", 3840)]), [])


class ChannelUrlTests(unittest.TestCase):
    def test_appends_videos_tab(self) -> None:
        self.assertEqual(
            normalize_channel_url("https://www.youtube.com/@somechannel"),
            "https://www.youtube.com/@somechannel/videos",
        )
        self.assertEqual(
            normalize_channel_url("@somechannel"),
            "https://www.youtube.com/@somechannel/videos",
        )

    def test_keeps_existing_tab(self) -> None:
        url = "https://www.youtube.com/channel/UCaaaaaaaaaaaaaaaaaaaa/videos"
        self.assertEqual(normalize_channel_url(url), url)

    def test_rejects_playlist_url(self) -> None:
        with self.assertRaises(ChannelError):
            normalize_channel_url("https://www.youtube.com/playlist?list=PLxxxxxxxxxxxxxxxxxxxxxx")

    def test_resolves_video_url_to_channel_videos_tab(self) -> None:
        class FakeYDL:
            def __init__(self, options: dict) -> None:
                pass

            def __enter__(self) -> "FakeYDL":
                return self

            def __exit__(self, _exc_type: object, _exc: object, _tb: object) -> None:
                return None

            def extract_info(self, url: str, download: bool = False) -> dict:
                return {"uploader_url": "https://www.youtube.com/@somechannel"}

        expected = "https://www.youtube.com/@somechannel/videos"
        with patch("app.youtube.urls.yt_dlp.YoutubeDL", FakeYDL):
            self.assertEqual(
                normalize_channel_url("https://www.youtube.com/watch?v=abcdefghijk"),
                expected,
            )
            self.assertEqual(
                normalize_channel_url("https://youtu.be/abcdefghijk?si=share"),
                expected,
            )
            self.assertEqual(
                normalize_channel_url("https://www.youtube.com/shorts/abcdefghijk"),
                expected,
            )

    def test_video_resolution_uses_channel_url(self) -> None:
        class FakeYDL:
            def __init__(self, options: dict) -> None:
                pass

            def __enter__(self) -> "FakeYDL":
                return self

            def __exit__(self, _exc_type: object, _exc: object, _tb: object) -> None:
                return None

            def extract_info(self, url: str, download: bool = False) -> dict:
                return {"channel_url": "https://www.youtube.com/channel/UCaaaaaaaaaaaaaaaaaaaa"}

        with patch("app.youtube.urls.yt_dlp.YoutubeDL", FakeYDL):
            self.assertEqual(
                normalize_channel_url("https://www.youtube.com/watch?v=abcdefghijk"),
                "https://www.youtube.com/channel/UCaaaaaaaaaaaaaaaaaaaa/videos",
            )


if __name__ == "__main__":
    unittest.main()
