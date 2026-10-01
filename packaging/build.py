"""Build a CompCreator desktop app for the OS you are running.

A Mac build produces one file, dist/CompCreator-mac.dmg. A Windows build
produces one file, dist/CompCreator-windows.exe. Run this on each operating
system; a Mac cannot produce the Windows app.
"""

from __future__ import annotations

import os
import shutil
import stat
import subprocess
import sys
from pathlib import Path
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
FRONTEND = ROOT / "frontend"
VENDOR = ROOT / "packaging" / "vendor"
DIST = ROOT / "dist"
BUILD = ROOT / "build"
VENV = BUILD / "venv"


def main() -> None:
    if sys.platform not in {"darwin", "win32"}:
        raise SystemExit("Build the desktop app on macOS or Windows.")
    _build_frontend()
    ffmpeg, ffprobe = _ensure_ffmpeg()
    pyinstaller = _venv_tool("pyinstaller")
    DIST.mkdir(parents=True, exist_ok=True)
    if (DIST / "CompCreator").exists():
        shutil.rmtree(DIST / "CompCreator")
    app_path = DIST / "CompCreator.app"
    if app_path.exists():
        shutil.rmtree(app_path)
    command = [
        str(pyinstaller),
        "--noconfirm",
        "--clean",
        "--windowed",
        "--name",
        "CompCreator",
        "--paths",
        str(ROOT / "backend"),
        "--distpath",
        str(DIST),
        "--workpath",
        str(BUILD / "pyinstaller"),
        "--specpath",
        str(BUILD),
        "--add-data",
        _pair(FRONTEND / "out", "frontend"),
        "--add-binary",
        _pair(ffmpeg, "."),
        "--add-binary",
        _pair(ffprobe, "."),
        "--collect-all",
        "yt_dlp",
        "--collect-all",
        "webview",
        "--collect-submodules",
        "app",
        "--hidden-import",
        "uvicorn.logging",
        "--hidden-import",
        "uvicorn.loops",
        "--hidden-import",
        "uvicorn.loops.auto",
        "--hidden-import",
        "uvicorn.protocols",
        "--hidden-import",
        "uvicorn.protocols.http",
        "--hidden-import",
        "uvicorn.protocols.http.auto",
        "--hidden-import",
        "uvicorn.protocols.websockets",
        "--hidden-import",
        "uvicorn.protocols.websockets.auto",
        "--hidden-import",
        "uvicorn.lifespan",
        "--hidden-import",
        "uvicorn.lifespan.on",
        "--osx-bundle-identifier",
        "app.compcreator.desktop",
        str(ROOT / "packaging" / "entry.py"),
    ]
    if sys.platform == "win32":
        command.insert(3, "--onefile")
    _run(command)
    archive = _package_product()
    print(f"Wrote {archive}")


def _build_frontend() -> None:
    if not (FRONTEND / "node_modules").exists():
        npm = shutil.which("npm")
        if not npm:
            raise SystemExit("npm is required to build the desktop UI.")
        _run([npm, "ci"], cwd=FRONTEND)
    env = os.environ.copy()
    env["DESKTOP_EXPORT"] = "1"
    env["NEXT_PUBLIC_API_URL"] = ""
    npm = shutil.which("npm")
    if not npm:
        raise SystemExit("npm is required to build the desktop UI.")
    _run([npm, "run", "build"], cwd=FRONTEND, env=env)
    if not (FRONTEND / "out" / "index.html").is_file():
        raise SystemExit("Next.js export did not write frontend/out/index.html.")


def _ensure_ffmpeg() -> tuple[Path, Path]:
    VENDOR.mkdir(parents=True, exist_ok=True)
    ffmpeg_name = "ffmpeg.exe" if sys.platform == "win32" else "ffmpeg"
    ffprobe_name = "ffprobe.exe" if sys.platform == "win32" else "ffprobe"
    ffmpeg = VENDOR / ffmpeg_name
    ffprobe = VENDOR / ffprobe_name
    if not (_binaries_match_machine(ffmpeg) and _binaries_match_machine(ffprobe)):
        for stale in (ffmpeg, ffprobe):
            stale.unlink(missing_ok=True)
        if sys.platform == "win32":
            _download_windows_ffmpeg(VENDOR)
        else:
            _download_mac_ffmpeg(VENDOR)
    if not ffmpeg.is_file() or not ffprobe.is_file():
        _copy_from_path(ffmpeg, ffprobe)
    if not ffmpeg.is_file() or not ffprobe.is_file():
        raise SystemExit(f"Could not find ffmpeg and ffprobe in {VENDOR}.")
    for binary in (ffmpeg, ffprobe):
        binary.chmod(binary.stat().st_mode | stat.S_IEXEC)
    return ffmpeg, ffprobe


_FFMPEG_RELEASE = "https://github.com/eugeneware/ffmpeg-static/releases/download/b6.1.1"


def _download_windows_ffmpeg(dest: Path) -> None:
    _download(f"{_FFMPEG_RELEASE}/ffmpeg-win32-x64.gz", dest / "ffmpeg.exe.gz")
    _download(f"{_FFMPEG_RELEASE}/ffprobe-win32-x64.gz", dest / "ffprobe.exe.gz")
    _gunzip(dest / "ffmpeg.exe.gz", dest / "ffmpeg.exe")
    _gunzip(dest / "ffprobe.exe.gz", dest / "ffprobe.exe")


def _download_mac_ffmpeg(dest: Path) -> None:
    arch = "arm64" if os.uname().machine == "arm64" else "x64"
    _download(f"{_FFMPEG_RELEASE}/ffmpeg-darwin-{arch}.gz", dest / "ffmpeg.gz")
    _download(f"{_FFMPEG_RELEASE}/ffprobe-darwin-{arch}.gz", dest / "ffprobe.gz")
    _gunzip(dest / "ffmpeg.gz", dest / "ffmpeg")
    _gunzip(dest / "ffprobe.gz", dest / "ffprobe")


def _gunzip(src: Path, dest: Path) -> None:
    import gzip

    with gzip.open(src, "rb") as packed, dest.open("wb") as handle:
        shutil.copyfileobj(packed, handle)


def _binaries_match_machine(path: Path) -> bool:
    if not path.is_file():
        return False
    if sys.platform != "darwin":
        return True
    info = subprocess.check_output(["file", str(path)], text=True)
    return os.uname().machine in info


def _copy_from_path(ffmpeg: Path, ffprobe: Path) -> None:
    for target, name in ((ffmpeg, "ffmpeg"), (ffprobe, "ffprobe")):
        found = shutil.which(name)
        if found and not target.exists():
            shutil.copy2(found, target)


def _download(url: str, dest: Path) -> None:
    print(f"Downloading {url}")
    request = Request(url, headers={"User-Agent": "CompCreator-packaging"})
    with urlopen(request, timeout=120) as response, dest.open("wb") as handle:
        shutil.copyfileobj(response, handle)


def _venv_tool(name: str) -> Path:
    if sys.platform == "win32":
        python = VENV / "Scripts" / "python.exe"
        tool = VENV / "Scripts" / f"{name}.exe"
    else:
        python = VENV / "bin" / "python"
        tool = VENV / "bin" / name
    if not python.exists():
        _run([sys.executable, "-m", "venv", str(VENV)])
    requirements = ROOT / "packaging" / "requirements-desktop.txt"
    _run([str(python), "-m", "pip", "install", "-r", str(requirements)])
    # A reused build/venv would otherwise keep the yt-dlp it first installed.
    _run([str(python), "-m", "pip", "install", "--upgrade", "yt-dlp"])
    if not tool.exists():
        raise SystemExit(f"{name} was not installed into {VENV}.")
    return tool


def _package_product() -> Path:
    if sys.platform == "darwin":
        source = DIST / "CompCreator.app"
        archive = DIST / "CompCreator-mac.dmg"
        if not source.exists():
            raise SystemExit(f"Expected {source}.")
        staging = BUILD / "dmg"
        if staging.exists():
            shutil.rmtree(staging)
        staging.mkdir(parents=True)
        shutil.copytree(source, staging / "CompCreator.app", symlinks=True)
        applications = staging / "Applications"
        if not applications.exists():
            applications.symlink_to("/Applications")
        if archive.exists():
            archive.unlink()
        _run(
            [
                "hdiutil",
                "create",
                "-volname",
                "CompCreator",
                "-srcfolder",
                str(staging),
                "-ov",
                "-format",
                "UDZO",
                str(archive),
            ]
        )
        return archive
    exe = DIST / "CompCreator.exe"
    if not exe.is_file():
        raise SystemExit(f"Expected {exe}.")
    archive = DIST / "CompCreator-windows.exe"
    if archive.exists():
        archive.unlink()
    exe.replace(archive)
    return archive


def _pair(src: Path, dest: str) -> str:
    return f"{src}{os.pathsep}{dest}"


def _run(command: list[str], cwd: Path | None = None, env: dict[str, str] | None = None) -> None:
    print("+", " ".join(command))
    subprocess.check_call(command, cwd=cwd, env=env)


if __name__ == "__main__":
    main()
