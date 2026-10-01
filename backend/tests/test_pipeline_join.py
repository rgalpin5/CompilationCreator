"""The join step's fallbacks: stream copy, then normalize and copy, then re-encode."""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, call, patch

from app.compilation import pipeline
from app.media.process import FfmpegError

JOB_DIR = Path("job")
PARTS = [JOB_DIR / "part_001.mp4", JOB_DIR / "part_002.mp4"]
RAWS = [JOB_DIR / "raw_001.mp4", JOB_DIR / "raw_002.mp4"]
NORMALIZED = [JOB_DIR / "norm_001.mp4", JOB_DIR / "norm_002.mp4"]
OUTPUT = JOB_DIR / "compilation.mp4"


def _join(concat: MagicMock, normalize: MagicMock, reencode: MagicMock) -> Path:
    store = MagicMock()
    with (
        patch.object(pipeline, "concat_clips", concat),
        patch.object(pipeline, "normalize_clip", normalize),
        patch.object(pipeline, "concat_reencode", reencode),
        patch.object(Path, "unlink"),
    ):
        return pipeline._join(store, "job", PARTS, RAWS, JOB_DIR, output_4k=False)


class JoinFallbackTests(unittest.TestCase):
    def test_matching_parts_are_joined_by_stream_copy(self) -> None:
        concat, normalize, reencode = MagicMock(), MagicMock(), MagicMock()
        self.assertEqual(_join(concat, normalize, reencode), OUTPUT)
        concat.assert_called_once_with(PARTS, OUTPUT)
        normalize.assert_not_called()
        reencode.assert_not_called()

    def test_failed_copy_normalizes_the_raw_clips_and_copies_again(self) -> None:
        concat = MagicMock(side_effect=[FfmpegError("copy failed"), None])
        normalize, reencode = MagicMock(), MagicMock()
        self.assertEqual(_join(concat, normalize, reencode), OUTPUT)
        self.assertEqual(concat.call_args_list, [call(PARTS, OUTPUT), call(NORMALIZED, OUTPUT)])
        self.assertEqual(
            normalize.call_args_list,
            [call(raw, norm, output_4k=False) for raw, norm in zip(RAWS, NORMALIZED, strict=True)],
        )
        reencode.assert_not_called()

    def test_working_files_are_removed_and_only_the_output_kept(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            job_dir = Path(tmp)
            output = job_dir / "compilation.mp4"
            names = ["raw_001.mp4", "part_001.mp4", "norm_001.mp4", "concat.txt"]
            for name in [*names, output.name]:
                (job_dir / name).write_bytes(b"x")
            (job_dir / "raw_002.mp4.part-Frag1").mkdir()
            pipeline._remove_working_files(job_dir, keep=output)
            self.assertEqual([entry.name for entry in job_dir.iterdir()], [output.name])

    def test_second_failed_copy_falls_back_to_a_full_reencode(self) -> None:
        concat = MagicMock(side_effect=FfmpegError("copy failed"))
        normalize, reencode = MagicMock(), MagicMock()
        self.assertEqual(_join(concat, normalize, reencode), OUTPUT)
        self.assertEqual(concat.call_count, 2)
        reencode.assert_called_once_with(NORMALIZED, OUTPUT)
