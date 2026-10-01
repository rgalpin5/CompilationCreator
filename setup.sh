#!/usr/bin/env bash
# Install CompCreator locally, or start it.
# Usage: ./setup.sh [setup|dev|lint|test]
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

python_ok() {
  "$1" -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 12) else 1)'
}

PYTHON=""
for candidate in python3.12 python3.13 python3.14 python3 python; do
  if command -v "$candidate" >/dev/null 2>&1 && python_ok "$candidate"; then
    PYTHON="$candidate"
    break
  fi
done

if [[ -z "$PYTHON" ]]; then
  echo "Python 3.12 or newer is required and was not found on PATH." >&2
  echo "Install it from https://www.python.org/downloads/ or your package manager." >&2
  exit 1
fi

exec "$PYTHON" -u "$ROOT/scripts/dev.py" "${1:-setup}"
