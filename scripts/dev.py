"""Set up and run CompCreator on macOS, Linux, and Windows.

``setup.sh`` and ``setup.bat`` select a Python 3.12+ interpreter and call
this module. The commands are:

- ``setup`` installs dependencies and writes local env files
- ``dev`` runs setup, then starts the API and the UI
- ``lint`` runs Ruff, mypy, ESLint, and the TypeScript compiler
- ``test`` runs the Python tests and the frontend unit tests
- ``api-types`` regenerates the frontend API types from the backend schema
"""

from __future__ import annotations

import argparse
import os
import shutil
import signal
import socket
import subprocess
import sys
import time
from pathlib import Path

from prereqs import (
    dev_command_hint,
    ffmpeg_install_hint,
    node_is_supported,
    python_is_supported,
    venv_python,
)

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
FRONTEND = ROOT / "frontend"
VENV = BACKEND / ".venv"


def main() -> None:
    parser = argparse.ArgumentParser(description="Set up and run CompCreator locally.")
    parser.add_argument(
        "command",
        nargs="?",
        default="setup",
        choices=("setup", "dev", "lint", "test", "api-types"),
    )
    args = parser.parse_args()
    commands = {
        "setup": cmd_setup,
        "dev": cmd_dev,
        "lint": cmd_lint,
        "test": cmd_test,
        "api-types": cmd_api_types,
    }
    commands[args.command]()


def cmd_setup() -> None:
    """Install the toolchain and write env files that are not already present."""
    _require_python()
    _require_node()
    _require_ffmpeg()
    python = _ensure_venv()
    _run([str(python), "-m", "pip", "install", "--upgrade", "pip"], cwd=BACKEND)
    _run(
        [
            str(python),
            "-m",
            "pip",
            "install",
            "-r",
            str(BACKEND / "requirements.txt"),
            "-r",
            str(BACKEND / "requirements-dev.txt"),
        ],
        cwd=BACKEND,
    )
    # The pin is a floor, so an existing virtualenv would keep an old yt-dlp.
    _run([str(python), "-m", "pip", "install", "--upgrade", "yt-dlp"], cwd=BACKEND)
    _run([_npm(), "ci"], cwd=FRONTEND)
    _copy_if_missing(ROOT / ".env.example", ROOT / ".env")
    _copy_if_missing(FRONTEND / ".env.example", FRONTEND / ".env.local")
    print()
    print("CompCreator is ready.")
    print("  API  http://localhost:8000")
    print("  UI   http://localhost:3000")
    print()
    print(f"Start both with: {dev_command_hint()}")
    print("Deno 2.3 or newer is optional. It is only needed when YouTube cookies are set.")


def cmd_dev() -> None:
    """Install anything missing, then run the API and the UI until Ctrl+C."""
    cmd_setup()
    _require_ports(8000, 3000)
    print("Starting the API on http://localhost:8000 and the UI on http://localhost:3000")
    _exit_on_hangup()
    backend = _spawn(
        [
            str(_venv_python()),
            "-m",
            "uvicorn",
            "app.main:app",
            "--reload",
            "--host",
            "127.0.0.1",
            "--port",
            "8000",
        ],
        cwd=BACKEND,
    )
    frontend: subprocess.Popen[bytes] | None = None
    try:
        frontend = _spawn([_npm(), "run", "dev"], cwd=FRONTEND)
        while True:
            if backend.poll() is not None:
                raise SystemExit("The API process stopped.")
            if frontend.poll() is not None:
                raise SystemExit("The UI process stopped.")
            time.sleep(0.4)
    except KeyboardInterrupt:
        print("\nStopping.")
    finally:
        _stop(backend)
        if frontend is not None:
            _stop(frontend)


def cmd_lint() -> None:
    """Run the Python and frontend linters."""
    python = _require_venv()
    npm = _npm()
    _run(
        [
            str(python),
            "-m",
            "ruff",
            "check",
            "app",
            "tests",
            "../scripts",
            "../packaging",
        ],
        cwd=BACKEND,
    )
    _run([str(python), "-m", "mypy"], cwd=BACKEND)
    # mypy only checks the sys.platform branch it runs on, so check Windows too.
    _run([str(python), "-m", "mypy", "--platform", "win32"], cwd=BACKEND)
    _run(
        [
            str(python),
            "-m",
            "mypy",
            "--python-version",
            "3.12",
            "--disallow-untyped-defs",
            "--disallow-incomplete-defs",
            "--check-untyped-defs",
            "--warn-redundant-casts",
            "--warn-unused-ignores",
            "--warn-return-any",
            "--strict-equality",
            "--extra-checks",
            "--no-warn-unused-configs",
            str(ROOT / "scripts" / "dev.py"),
            str(ROOT / "scripts" / "prereqs.py"),
        ],
        cwd=ROOT,
    )
    _run([npm, "run", "lint"], cwd=FRONTEND)
    _run([npm, "run", "api-types:check"], cwd=FRONTEND)
    _run([npm, "run", "typecheck"], cwd=FRONTEND)


def cmd_test() -> None:
    """Run the backend tests, the setup-script tests, and the frontend unit tests."""
    python = _require_venv()
    env = os.environ.copy()
    env["PYTHONPATH"] = str(BACKEND)
    _run([str(python), "-m", "unittest", "discover", "-s", "tests"], cwd=BACKEND, env=env)
    _run(
        [str(python), "-m", "unittest", "discover", "-s", "scripts", "-p", "test_*.py"],
        cwd=ROOT,
    )
    _run([_npm(), "test"], cwd=FRONTEND)


def cmd_api_types() -> None:
    """Write the backend's OpenAPI schema, then generate the frontend types from it."""
    python = _require_venv()
    env = os.environ.copy()
    env["PYTHONPATH"] = str(BACKEND)
    _run([str(python), "-m", "app.openapi_schema"], cwd=BACKEND, env=env)
    _run([_npm(), "run", "api-types"], cwd=FRONTEND)


def _require_python() -> None:
    info = sys.version_info
    if python_is_supported((info.major, info.minor, info.micro)):
        return
    found = ".".join(str(part) for part in sys.version_info[:3])
    raise SystemExit(f"Python 3.12 or newer is required. This interpreter is {found}.")


def _require_node() -> None:
    node = shutil.which("node")
    if node is None or shutil.which("npm") is None:
        raise SystemExit(
            "Node.js 20 or newer and npm are required. Install them from https://nodejs.org/."
        )
    raw = subprocess.check_output([node, "--version"], text=True).strip()
    if node_is_supported(raw):
        return
    raise SystemExit(f"Node.js 20 or newer is required. Found {raw}.")


def _require_ffmpeg() -> None:
    missing = [name for name in ("ffmpeg", "ffprobe") if shutil.which(name) is None]
    if not missing:
        return
    names = " and ".join(missing)
    raise SystemExit(f"Could not find {names} on PATH.\n{ffmpeg_install_hint()}")


def _ensure_venv() -> Path:
    python = _venv_python()
    if python.is_file() and _interpreter_ok(python):
        return python
    if VENV.exists():
        print(f"Replacing {VENV.relative_to(ROOT)} because it is not Python 3.12 or newer.")
        shutil.rmtree(VENV)
    print(f"Creating {VENV.relative_to(ROOT)}")
    _run([sys.executable, "-m", "venv", str(VENV)], cwd=ROOT)
    if not python.is_file():
        raise SystemExit(f"The virtualenv was not created at {python}.")
    return python


def _interpreter_ok(python: Path) -> bool:
    probe = "import sys; raise SystemExit(0 if sys.version_info >= (3, 12) else 1)"
    result = subprocess.run([str(python), "-c", probe], check=False)
    return result.returncode == 0


def _require_venv() -> Path:
    python = _venv_python()
    if python.is_file():
        return python
    raise SystemExit(f"Run {dev_command_hint().removesuffix(' dev')} before this command.")


def _venv_python() -> Path:
    return venv_python(VENV)


def _npm() -> str:
    found = shutil.which("npm")
    if found is None:
        raise SystemExit("npm was not found on PATH.")
    return found


def _copy_if_missing(example: Path, dest: Path) -> None:
    relative = dest.relative_to(ROOT)
    if dest.exists():
        print(f"Keeping {relative}")
        return
    if not example.is_file():
        raise SystemExit(f"Missing {example.relative_to(ROOT)}.")
    dest.write_text(example.read_text(encoding="utf-8"), encoding="utf-8")
    print(f"Wrote {relative}")


def _require_ports(*ports: int) -> None:
    busy = [str(port) for port in ports if _port_open(port)]
    if not busy:
        return
    listed = ", ".join(busy)
    raise SystemExit(f"Port {listed} is already in use. Stop the other process and try again.")


def _port_open(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.3)
        return sock.connect_ex(("127.0.0.1", port)) == 0


def _run(command: list[str], *, cwd: Path, env: dict[str, str] | None = None) -> None:
    print("+", " ".join(command), flush=True)
    try:
        subprocess.run(command, cwd=cwd, env=env, check=True)
    except subprocess.CalledProcessError as exc:
        raise SystemExit(exc.returncode) from exc
    except OSError as exc:
        raise SystemExit(f"Could not run {command[0]}: {exc}") from exc


def _spawn(command: list[str], *, cwd: Path) -> subprocess.Popen[bytes]:
    """Start ``command`` in its own process group so ``_stop`` can end all of it.

    The terminal's Ctrl+C then reaches only this script, and ``cmd_dev`` stops
    the children itself.
    """
    print("+", " ".join(command), flush=True)
    try:
        if sys.platform == "win32":
            return subprocess.Popen(
                command, cwd=cwd, creationflags=subprocess.CREATE_NEW_PROCESS_GROUP
            )
        return subprocess.Popen(command, cwd=cwd, start_new_session=True)
    except OSError as exc:
        raise SystemExit(f"Could not start {command[0]}: {exc}") from exc


def _exit_on_hangup() -> None:
    """Unwind through ``cmd_dev``'s cleanup when the terminal closes or on SIGTERM.

    The children run in their own sessions, so these signals no longer reach them.
    """
    if sys.platform == "win32":
        return

    def leave(signum: int, _frame: object) -> None:
        raise SystemExit(128 + signum)

    signal.signal(signal.SIGHUP, leave)
    signal.signal(signal.SIGTERM, leave)


def _stop(process: subprocess.Popen[bytes], *, timeout: float = 8) -> None:
    """Stop ``process`` and the children it started.

    ``npm run dev`` starts ``node`` as a child, so stopping only ``npm`` would
    leave the Next.js server running. The whole process group is signalled.
    """
    if sys.platform == "win32":
        if process.poll() is not None:
            return
        subprocess.run(
            ["taskkill", "/F", "/T", "/PID", str(process.pid)],
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return
    # The group outlives its leader, so signal it even when npm has exited.
    group = process.pid
    if not _signal_group(group, signal.SIGTERM):
        process.poll()
        return
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        process.poll()
        if not _signal_group(group, 0):
            return
        time.sleep(0.1)
    _signal_group(group, signal.SIGKILL)
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        return


def _signal_group(group: int, sig: int) -> bool:
    """Send ``sig`` to process group ``group``. Return False once the group is gone."""
    if sys.platform == "win32":
        return False
    try:
        os.killpg(group, sig)
    except ProcessLookupError:
        return False
    except PermissionError:
        # macOS answers this way while the leader is exiting but not yet reaped.
        # The caller's poll() reaps it, and the next call sees the group gone.
        return True
    return True


if __name__ == "__main__":
    main()
