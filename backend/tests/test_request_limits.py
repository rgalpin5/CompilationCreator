"""Oversized request bodies are rejected while they are parsed."""

import unittest

from pydantic import ValidationError

from app.compilation.validate import MAX_CLIPS
from app.models import Clip, CompilationRequest


def _clip(**fields: object) -> dict[str, object]:
    return {"video_id": "abcdefghijk", "start": "0:00", "end": "0:10", **fields}


class RequestLimitTests(unittest.TestCase):
    def test_ordinary_clip_is_accepted(self) -> None:
        clip = Clip.model_validate(_clip(title="A title", thumbnail="https://i.ytimg.com/x.jpg"))
        self.assertEqual(clip.title, "A title")

    def test_long_title_is_cut_but_an_absurd_one_is_rejected(self) -> None:
        self.assertEqual(len(Clip.model_validate(_clip(title="t" * 500)).title), 200)
        with self.assertRaises(ValidationError):
            Clip.model_validate(_clip(title="t" * 5000))

    def test_oversized_text_fields_are_rejected(self) -> None:
        for field, size in (("start", 50), ("end", 50), ("channel", 5000), ("thumbnail", 5000)):
            with self.subTest(field=field), self.assertRaises(ValidationError):
                Clip.model_validate(_clip(**{field: "x" * size}))

    def test_clip_count_has_a_hard_cap_above_the_readable_one(self) -> None:
        # Just over MAX_CLIPS still parses, so validate.py can explain the limit.
        CompilationRequest.model_validate({"clips": [_clip()] * (MAX_CLIPS + 1)})
        with self.assertRaises(ValidationError):
            CompilationRequest.model_validate({"clips": [_clip()] * 1001})


if __name__ == "__main__":
    unittest.main()
