"""Load a local dotenv file without overriding the process environment.

The supported syntax is one ``KEY=VALUE`` pair per line. A leading ``export``
is optional. Values may be wrapped in single or double quotes. Blank lines
and full-line comments are ignored. Existing variables win, and a missing
file is a no-op so hosted deploys can rely on real environment variables.
"""

from __future__ import annotations

from collections.abc import MutableMapping
from pathlib import Path

from app.errors import ConfigurationError


def load_env_file(path: Path, environ: MutableMapping[str, str]) -> None:
    """Apply assignments from ``path`` for keys that are not already set.

    A missing file is ignored. A file that cannot be read, or that is not
    UTF-8, raises ``ConfigurationError`` with a message that names ``path``.
    Lines that are not assignments are skipped.
    """
    if not path.exists():
        return
    if not path.is_file():
        raise ConfigurationError(f"{path} is not a file.")
    try:
        text = path.read_text(encoding="utf-8")
    except PermissionError as exc:
        raise ConfigurationError(f"Permission denied reading {path}.") from exc
    except UnicodeDecodeError as exc:
        raise ConfigurationError(f"{path} is not valid UTF-8.") from exc
    except OSError as exc:
        detail = exc.strerror or "the operating system rejected the request"
        raise ConfigurationError(f"Could not read {path}: {detail}.") from exc
    for raw_line in text.splitlines():
        parsed = _parse_assignment(raw_line)
        if parsed is None:
            continue
        key, value = parsed
        environ.setdefault(key, value)


def _parse_assignment(raw_line: str) -> tuple[str, str] | None:
    line = raw_line.strip()
    if not line or line.startswith("#"):
        return None
    if line.startswith("export "):
        line = line[len("export ") :].strip()
    key, separator, value = line.partition("=")
    if separator != "=":
        return None
    name = key.strip()
    if not _is_env_name(name):
        return None
    return name, _unquote(value.strip())


def _is_env_name(name: str) -> bool:
    if not name or name[0].isdigit():
        return False
    return all(character.isalnum() or character == "_" for character in name)


def _unquote(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        return value[1:-1]
    return value
