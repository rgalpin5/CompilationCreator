import subprocess
import tempfile
import unittest
from pathlib import Path

from app.media.concat import concat_clips
from app.media.plan import fit_4k, prep_plan
from app.media.probe import StreamLayout, probe_layout
from app.youtube.download import use_concurrent_download


def _clip(path: Path, size: str) -> None:
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-f",
            "lavfi",
            "-i",
            f"testsrc=size={size}:rate=30:duration=1",
            "-f",
            "lavfi",
            "-i",
            "sine=frequency=440:duration=1",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            str(path),
        ],
        check=True,
        capture_output=True,
    )


def _layout(
    height: int = 1080,
    frame_rate: str = "30/1",
    sample_rate: str = "44100",
    channels: int = 2,
) -> StreamLayout:
    return StreamLayout(
        "h264",
        height * 16 // 9,
        height,
        "yuv420p",
        frame_rate,
        "1/15360",
        "High",
        "aac",
        sample_rate,
        channels,
        "1/44100",
    )


class StreamCopyTests(unittest.TestCase):
    def test_matching_clips_join_without_reencode(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            first = root / "a.mp4"
            second = root / "b.mp4"
            output = root / "compilation.mp4"
            _clip(first, "320x240")
            _clip(second, "320x240")
            layouts = [probe_layout(first), probe_layout(second)]
            self.assertIsNotNone(layouts[0])
            self.assertEqual(layouts[0], layouts[1])
            concat_clips([first, second], output)
            joined = probe_layout(output)
            self.assertIsNotNone(joined)
            assert joined is not None
            first_layout = layouts[0]
            assert first_layout is not None
            self.assertEqual(joined.video_codec, first_layout.video_codec)
            self.assertEqual((joined.width, joined.height), (320, 240))

    def test_different_sizes_do_not_match(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            first = root / "a.mp4"
            second = root / "b.mp4"
            _clip(first, "320x240")
            _clip(second, "640x480")
            self.assertNotEqual(probe_layout(first), probe_layout(second))


class PrepPlanTests(unittest.TestCase):
    def _modes(self, layouts: list[StreamLayout]) -> list[str]:
        return [prep.mode for prep in prep_plan(layouts)]

    def test_identical_clips_keep(self) -> None:
        self.assertEqual(self._modes([_layout(), _layout(), _layout()]), ["keep"] * 3)

    def test_different_audio_remuxes_only_that_clip(self) -> None:
        layouts = [_layout(), _layout(sample_rate="48000"), _layout()]
        self.assertEqual(self._modes(layouts), ["keep", "audio", "keep"])

    def test_different_height_encodes_only_that_clip(self) -> None:
        layouts = [_layout(), _layout(height=720), _layout()]
        self.assertEqual(self._modes(layouts), ["keep", "video", "keep"])

    def test_ntsc_and_integer_frame_rate_share_bucket(self) -> None:
        layouts = [_layout(frame_rate="30/1"), _layout(frame_rate="30000/1001")]
        self.assertEqual(self._modes(layouts), ["keep", "keep"])

    def test_4k_export_scales_smaller_clips_and_keeps_real_4k(self) -> None:
        layouts = [_layout(height=2160), _layout(height=1080)]
        plan = fit_4k(prep_plan(layouts), layouts)
        self.assertEqual([prep.mode for prep in plan], ["keep", "video"])
        self.assertTrue(all((prep.width, prep.height) == (3840, 2160) for prep in plan))


class ConcurrentDownloadTests(unittest.TestCase):
    def test_unknown_duration_uses_concurrent(self) -> None:
        self.assertTrue(use_concurrent_download(0, 60, None))

    def test_little_wasted_time_uses_concurrent(self) -> None:
        self.assertTrue(use_concurrent_download(30, 60, 120))

    def test_large_share_of_video_uses_concurrent(self) -> None:
        self.assertTrue(use_concurrent_download(0, 1200, 3600))

    def test_short_slice_of_long_video_uses_sections(self) -> None:
        self.assertFalse(use_concurrent_download(3600, 3720, 4 * 3600))


if __name__ == "__main__":
    unittest.main()
