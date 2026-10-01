"""Keep the committed OpenAPI schema, and so the frontend types, in step with the API."""

import io
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

from app.openapi_schema import SCHEMA_PATH, main, schema_json


class OpenApiSchemaTests(unittest.TestCase):
    def test_committed_schema_matches_the_app(self) -> None:
        committed = SCHEMA_PATH.read_text(encoding="utf-8") if SCHEMA_PATH.is_file() else ""
        self.assertTrue(
            committed == schema_json(),
            f"{SCHEMA_PATH.name} is out of date. Run ./setup.sh api-types and commit the result.",
        )

    def test_main_writes_to_the_given_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "openapi.json"
            with (
                patch("app.openapi_schema.sys.argv", ["openapi_schema", str(target)]),
                redirect_stdout(io.StringIO()) as out,
            ):
                main()
            self.assertEqual(target.read_text(encoding="utf-8"), schema_json())
        self.assertIn(str(target), out.getvalue())
