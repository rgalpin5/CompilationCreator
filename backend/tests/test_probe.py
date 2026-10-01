import json
import subprocess
import unittest
from collections.abc import Callable
from pathlib import Path
from unittest.mock import patch

from app.errors import ConfigurationError
from app.jobs.runner import runner
from app.media import probe

_STREAMS = {
    "streams": [
        {
            "codec_type": "video",
            "codec_name": "h264",
            "width": 1920,
            "height": 1080,
            "pix_fmt": "yuv420p",
            "avg_frame_rate": "30/1",
            "time_base": "1/15360",
            "profile": "High",
        },
        {
            "codec_type": "audio",
            "codec_name": "aac",
            "sample_rate": "48000",
            "channels": 2,
            "time_base": "1/48000",
        },
    ]
}


def _answer(
    stdout: str, returncode: int = 0
) -> Callable[[list[str]], subprocess.CompletedProcess[str]]:
    def run(command: list[str]) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(command, returncode, stdout=stdout, stderr="")

    return run


class ProbeTests(unittest.TestCase):
    def test_layout_runs_through_the_cancellable_runner(self) -> None:
        with patch.object(runner, "run", side_effect=_answer(json.dumps(_STREAMS))) as run:
            layout = probe.probe_layout(Path("clip.mp4"))
        run.assert_called_once()
        assert layout is not None
        self.assertEqual((layout.video_codec, layout.width, layout.channels), ("h264", 1920, 2))

    def test_unreadable_output_means_no_layout(self) -> None:
        for stdout in ("not json", "0", "[]", "{}"):
            with self.subTest(stdout=stdout), patch.object(runner, "run", _answer(stdout)):
                self.assertIsNone(probe.probe_layout(Path("clip.mp4")))
        with patch.object(runner, "run", _answer("", returncode=1)):
            self.assertIsNone(probe.probe_layout(Path("clip.mp4")))

    def test_missing_ffprobe_is_a_configuration_error(self) -> None:
        with patch.object(runner, "run", side_effect=FileNotFoundError("ffprobe")):
            with self.assertRaises(ConfigurationError):
                probe.probe_layout(Path("clip.mp4"))
            with self.assertRaises(ConfigurationError):
                probe._probe_duration(Path("clip.mp4"))


if __name__ == "__main__":
    unittest.main()
