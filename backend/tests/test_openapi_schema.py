"""Keep the committed OpenAPI schema, and so the frontend types, in step with the API."""

import unittest

from app.openapi_schema import SCHEMA_PATH, schema_json


class OpenApiSchemaTests(unittest.TestCase):
    def test_committed_schema_matches_the_app(self) -> None:
        committed = SCHEMA_PATH.read_text(encoding="utf-8") if SCHEMA_PATH.is_file() else ""
        self.assertTrue(
            committed == schema_json(),
            f"{SCHEMA_PATH.name} is out of date. Run ./setup.sh api-types and commit the result.",
        )
