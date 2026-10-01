"""Load a local dotenv file without overriding the process environment.

The supported syntax is one ``KEY=VALUE`` pair per line. A leading ``export``
is optional. Values may be wrapped in single or double quotes. Blank lines
and full-line comments are ignored, and so is a `` # comment`` after an
unquoted value. Existing variables win, and a missing file is a no-op so
hosted deploys can rely on real environment variables.
"""

from __future__ import annotations

import re
from collections.abc import MutableMapping
from pathlib import Path

from app.errors import ConfigurationError

# In an unquoted value, a "#" after whitespace starts a comment.
_INLINE_COMMENT = re.compile(r"\s#")


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
    return name, _parse_value(value)


def _is_env_name(name: str) -> bool:
    if not name or name[0].isdigit():
        return False
    return all(character.isalnum() or character == "_" for character in name)


def _parse_value(value: str) -> str:
    """Unquote ``value``, or drop a trailing `` # comment`` when it is unquoted.

    Quoted values keep ``#`` verbatim. In an unquoted value only a ``#`` that
    follows whitespace starts a comment, so ``a#b`` stays as written. The
    whitespace may be the gap after ``=``, so ``KEY= # note`` is empty.
    """
    uncommented = _INLINE_COMMENT.split(value, maxsplit=1)[0].strip()
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        return value[1:-1]
    if value[:1] in {"'", '"'}:
        closing = value.find(value[0], 1)
        if closing > 0:
            rest = value[closing + 1 :]
            if rest[:1].isspace() and rest.strip().startswith("#"):
                return value[1:closing]
    return uncommented
