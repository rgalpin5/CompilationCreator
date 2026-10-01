"""Write the API's OpenAPI schema for the frontend type generator.

``./setup.sh api-types`` runs this module, then generates
``frontend/lib/api/schema.gen.ts`` from the JSON it writes. A backend test
fails when the committed JSON no longer matches the app.
"""

import json
import sys
from pathlib import Path

from app.main import app

SCHEMA_PATH = Path(__file__).resolve().parents[2] / "frontend" / "lib" / "api" / "openapi.json"


def schema_json() -> str:
    """The schema as stable, diff-friendly JSON."""
    return json.dumps(app.openapi(), indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def main() -> None:
    target = Path(sys.argv[1]) if len(sys.argv) > 1 else SCHEMA_PATH
    target.write_text(schema_json(), encoding="utf-8", newline="\n")
    print(f"Wrote {target}")


if __name__ == "__main__":
    main()
