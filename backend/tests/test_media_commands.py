import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from app.errors import ConfigurationError
from app.media.concat import concat_clips, concat_reencode
from app.media.encode import finalize_clip, normalize_clip
from app.media.plan import Prep
from app.media.probe import StreamLayout
from app.media.process import FfmpegError, _run


def _done(
    returncode: int = 0, stdout: str = "", stderr: str = ""
) -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess(["ffmpeg"], returncode, stdout, stderr)


def _layout(audio_codec: str = "aac") -> StreamLayout:
    return StreamLayout(
        "h264", 1920, 1080, "yuv420p", "30/1", "1/15360", "High", audio_codec, "48000", 2, "1/48000"
    )


class RunTests(unittest.TestCase):
    def test_success_returns_quietly(self) -> None:
        with patch("app.media.process.runner.run", return_value=_done()):
            _run(["ffmpeg", "-version"])

    def test_missing_program_names_it(self) -> None:
        with (
            patch("app.media.process.runner.run", side_effect=FileNotFoundError()),
            self.assertRaises(ConfigurationError) as caught,
        ):
            _run(["/opt/bin/ffprobe", "-version"])
        self.assertIn("ffprobe was not found", str(caught.exception))

    def test_failure_keeps_the_tail_of_stderr(self) -> None:
        stderr = "x" * 1000 + "the real reason"
        with (
            patch("app.media.process.runner.run", return_value=_done(1, stderr=stderr)),
            self.assertRaises(FfmpegError) as caught,
        ):
            _run(["ffmpeg"])
        self.assertEqual(len(str(caught.exception)), 800)
        self.assertTrue(str(caught.exception).endswith("the real reason"))

    def test_failure_with_no_output_has_a_sentence(self) -> None:
        with (
            patch("app.media.process.runner.run", return_value=_done(1)),
            self.assertRaises(FfmpegError) as caught,
        ):
            _run(["ffmpeg"])
        self.assertEqual(str(caught.exception), "ffmpeg failed")

    def test_failure_falls_back_to_stdout(self) -> None:
        with (
            patch("app.media.process.runner.run", return_value=_done(1, stdout=" out \n")),
            self.assertRaises(FfmpegError) as caught,
        ):
            _run(["ffmpeg"])
        self.assertEqual(str(caught.exception), "out")


class NormalizeClipTests(unittest.TestCase):
    def _command(self, layout: StreamLayout | None, *, output_4k: bool = False) -> list[str]:
        with (
            patch("app.media.encode.probe_layout", return_value=layout),
            patch("app.media.encode._run") as run,
        ):
            normalize_clip(Path("in.mp4"), Path("out.mp4"), output_4k=output_4k)
        command: list[str] = run.call_args.args[0]
        return command

    def test_clip_with_audio_maps_its_own_track(self) -> None:
        command = self._command(_layout())
        graph = command[command.index("-filter_complex") + 1]
        self.assertIn("[0:a:0]aformat", graph)
        self.assertIn("scale=1920:1080", graph)
        self.assertNotIn("-shortest", command)
        self.assertEqual(command[command.index("-level:v") + 1], "4.0")
        self.assertEqual(command[-1], "out.mp4")

    def test_silent_clip_gets_a_generated_track(self) -> None:
        command = self._command(_layout(audio_codec=""))
        self.assertIn("anullsrc=channel_layout=stereo:sample_rate=48000", command)
        self.assertIn("-shortest", command)
        self.assertIn("1:a:0", command)

    def test_unprobed_clip_is_treated_as_silent(self) -> None:
        command = self._command(None)
        self.assertIn("-shortest", command)

    def test_4k_uses_a_larger_frame_and_level(self) -> None:
        command = self._command(_layout(), output_4k=True)
        graph = command[command.index("-filter_complex") + 1]
        self.assertIn("scale=3840:2160", graph)
        self.assertEqual(command[command.index("-level:v") + 1], "5.1")


class FinalizeClipTests(unittest.TestCase):
    def _command(self, prep: Prep) -> list[str]:
        with patch("app.media.encode._run") as run:
            finalize_clip(Path("in.mp4"), Path("out.mp4"), prep)
        command: list[str] = run.call_args.args[0]
        return command

    def test_keep_copies_every_stream(self) -> None:
        command = self._command(Prep("keep", 1920, 1080, 30, "aac", "48000", 2))
        self.assertEqual(command[4:6], ["-c", "copy"])
        self.assertEqual(command[-1], "out.mp4")

    def test_audio_reencodes_opus_with_libopus(self) -> None:
        command = self._command(Prep("audio", 1920, 1080, 30, "opus", "48000", 2))
        self.assertEqual(command[command.index("-c:a") + 1], "libopus")
        self.assertEqual(command[command.index("-ar") + 1], "48000")
        self.assertEqual(command[command.index("-ac") + 1], "2")

    def test_audio_without_rate_or_channels_leaves_them_alone(self) -> None:
        command = self._command(Prep("audio", 1920, 1080, 30, "aac", "", 0))
        self.assertEqual(command[command.index("-c:a") + 1], "aac")
        self.assertNotIn("-ar", command)
        self.assertNotIn("-ac", command)

    def test_video_scales_to_the_target_frame(self) -> None:
        command = self._command(Prep("video", 1280, 720, 25, "aac", "48000", 2))
        self.assertIn("scale=1280:720", command[command.index("-vf") + 1])
        self.assertEqual(command[command.index("-r") + 1], "25")

    def test_unknown_mode_is_rejected(self) -> None:
        with patch("app.media.encode._run") as run, self.assertRaises(ValueError):
            finalize_clip(Path("in.mp4"), Path("out.mp4"), Prep("bogus", 1, 1, 1, "", "", 0))
        run.assert_not_called()


class ConcatTests(unittest.TestCase):
    def test_list_file_escapes_quotes_and_uses_forward_slashes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            clips = [root / "a.mp4", root / "it's.mp4"]
            dest = root / "final.mp4"
            with patch("app.media.concat._run") as run:
                concat_clips(clips, dest)
            text = (root / "concat.txt").read_text(encoding="utf-8")
        lines = text.splitlines()
        self.assertEqual(len(lines), 2)
        self.assertTrue(lines[0].startswith("file '") and lines[0].endswith("a.mp4'"))
        self.assertIn("it'\\''s.mp4", lines[1])
        self.assertNotIn("\\\\", text)
        command = run.call_args.args[0]
        self.assertEqual(command[command.index("-i") + 1], str(root / "concat.txt"))
        self.assertEqual(command[-1], str(dest))

    def test_reencode_wires_every_input_into_the_filter(self) -> None:
        with patch("app.media.concat._run") as run:
            concat_reencode([Path("a.mp4"), Path("b.mp4"), Path("c.mp4")], Path("out.mp4"))
        command = run.call_args.args[0]
        self.assertEqual(command.count("-i"), 3)
        graph = command[command.index("-filter_complex") + 1]
        self.assertEqual(
            graph, "[0:v:0][0:a:0][1:v:0][1:a:0][2:v:0][2:a:0]concat=n=3:v=1:a=1[v][a]"
        )


if __name__ == "__main__":
    unittest.main()
