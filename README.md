# CompCreator

CompCreator builds one MP4 from videos on a YouTube channel. Paste a channel URL, choose the videos, cut each intro and outro, reorder the timeline, and export a single file. A log records which videos have already been used and which compilations have been finished.

This is a personal tool. There is no authentication. YouTube’s Terms of Service restrict downloading content. Use it only for videos you own or otherwise have the right to download and reuse.

## What the app does

The interface is one page with two views.

**Editor**

1. Load a channel. The first page is 24 videos. Scrolling loads the next page, up to 50 videos per request.
2. Click a thumbnail to add it to the timeline. Click it again to remove it. Reorder with the up and down controls.
3. Open the cut step. Each clip plays in an embedded YouTube player. Mark where the intro ends and where the outro begins, or keep the full video.
4. Start the export. Clips download together. Matching picture and audio are joined by stream copy. A clip is re-encoded only when its picture or audio does not match the others. Optional 4K output writes a 3840×2160 file and scales smaller sources up to that frame; it does not invent detail.
5. When the job is ready, save the MP4 to Downloads or to a folder you type. Saving copies the finished file out, then deletes the working clips for that job.

A pasted video URL (`/watch`, `/shorts`, `/live`, `/embed`, or `youtu.be`) is resolved to that uploader’s channel. Handles (`@name`), `/channel/UC…`, `/c/…`, and `/user/…` URLs are accepted. Playlists are rejected.

**Logs**

After an export finishes, the app records each distinct video once and names the compilation from the local date and time (for example `29 Sep, 17:04.mp4`). The Logs view searches and sorts that history. The last 200 compilations are kept.

## Architecture

```text
Browser or desktop window
        │
        ▼
Next.js UI  ──HTTP──►  FastAPI
                         │
                         ├─ yt-dlp     list a channel, download clips
                         ├─ ffmpeg     trim, match formats, concatenate
                         └─ local disk job folders + usage.json
```

An export does not run inside the HTTP request that starts it. `POST /api/compilations` validates the timeline, creates a job, and returns `202` with a job id. A background task then moves the job through `queued` → `downloading` → `concatenating` → `ready`. Failure sets `failed`. Cancel sets `cancelled` and deletes the job folder. Saving a finished file sets `saved`.

The UI polls `GET /api/compilations/{job_id}` every two seconds until the job leaves the active states. Keep the page open while an export runs. A long compilation needs substantial disk space: each clip can exist as a raw download, a prepared part, and the joined file until you save. A failed export deletes its working files. When the API starts and before each new export, it deletes finished jobs nobody saved and leftover job folders (from a crash or restart) that have not changed in 24 hours. Only folders named like a job id are touched, and running exports are never removed.

### Download and join strategy

For each clip the backend chooses one of two downloads:

- **Whole video, then a local trim**, when the duration is unknown, when the unused portion is 90 seconds or less, or when the kept span is at least 15% of the video. The download uses 16 concurrent fragments. ffmpeg then stream-copies the requested range. A clip that already covers essentially the whole file is renamed instead of trimmed.
- **Section download**, when the clip is a small slice of a long upload. yt-dlp requests that range directly.

Format selection prefers H.264 video and AAC audio at or below 1080p, or at or below 2160p when 4K output is on, so later clips can be copied instead of re-encoded.

Before the join, each file is probed. The most common picture layout (codec, size, pixel format, frame rate) and the most common audio layout on that picture become the target. Each clip is then kept as-is, audio-re-encoded, or picture-re-encoded. The join uses the ffmpeg concat demuxer with stream copy. If that fails, every clip is normalized to H.264, AAC, 30 fps, and either 1920×1080 or 3840×2160, then copied. If the copy still fails, the clips are joined with the concat filter and a re-encode.

### YouTube access

Listing and downloading go through the `yt-dlp` Python library in-process. A cookie source is optional and is resolved in this order:

1. `YTDLP_COOKIES_FILE` — path to a Netscape `cookies.txt`.
2. `YTDLP_COOKIES` — the file contents, or those contents encoded as base64.
3. `YTDLP_COOKIES_BROWSER` — browser name (`chrome`, `brave`, `edge`, `firefox`, `safari`). The desktop app sets this to the first installed browser, unless it is `none`.

When cookies are sent, yt-dlp must solve YouTube’s player challenge. That requires Deno 2.3 or newer. Set `YTDLP_DENO` to the binary if it is not on `PATH` or in the usual install locations (`~/.deno/bin`, Homebrew on macOS).

The desktop app does not share a YouTube login. Each install reads cookies from a browser on that computer. The first download on macOS may prompt for Keychain access so the app can read those cookies. Allow it.

## Tech stack

| Layer | Choice |
| --- | --- |
| UI | Next.js 16 (App Router), React 19, TypeScript, Tailwind CSS 4 |
| UI kit | shadcn (`base-nova`), Base UI, class-variance-authority |
| API | Python 3.12, FastAPI, Pydantic v2, Uvicorn |
| Media | yt-dlp, ffmpeg, ffprobe |
| Desktop window | pywebview, packaged with PyInstaller |
| Hosted deploy | FastAPI on Cloud Run behind a shared password; the Next.js UI optionally on Vercel |
| Local container | Docker Compose runs the backend only (`python:3.12-slim` plus ffmpeg) |

Job state is in memory. Finished files and the usage log are on local disk. Nothing is shared across processes or instances. Restarting the API drops in-flight jobs. The usage file survives if `JOBS_DIR` does.

## Repository layout

```text
CompCreator/
  backend/                 FastAPI application
    app/main.py            app, CORS, router wiring, store startup
    app/config.py          jobs directory and CORS
    app/models.py          request and response models
    app/timeparse.py       mm:ss and hh:mm:ss
    app/hardware.py        CPU-sized download and encode pools
    app/delivery.py        save path and the copy-then-delete handoff
    app/desktop/           window, paths, browser, local server
    app/routers/           channels, compilations, usage, store dependencies
    app/youtube/           URL normalization, listing, cookies, download
    app/media/             probe, prep plan, encode, concat
    app/compilation/       timeline checks and the export pipeline
    app/jobs/              job store and process runner
    app/usage/             compilation log
    tests/                 unittest modules
    Dockerfile
    requirements.txt       runtime packages (mirrors pyproject.toml)
    requirements-dev.txt   ruff and mypy
    pyproject.toml         dependencies plus Ruff and mypy settings
  frontend/                Next.js UI
    app/page.tsx           editor and logs view switch
    features/              channel, timeline, cuts, player, export, logs
    components/ui/         shadcn
    lib/api/               browser API client and generated API types
    lib/time.ts            client-side time checks
  packaging/               desktop build (PyInstaller, bundled ffmpeg)
  scripts/dev.py           shared local setup and run implementation
  setup.sh                 macOS and Linux entry point
  setup.bat                Windows entry point
  docker-compose.yml       backend only
  vercel.json              Next.js UI on Vercel (the API runs on Cloud Run)
  dist/                    local desktop build output (git-ignored)
```

## API

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/health` | `{ "ok": true }` |
| `GET` | `/api/session` | `200` when the request may use the API, `401` when the password is missing or wrong, `429` after too many wrong passwords from this client |
| `POST` | `/api/channels?limit=&offset=` | One page of videos for a channel URL |
| `POST` | `/api/compilations` | Start an export. Returns `202` and a job |
| `GET` | `/api/compilations/{job_id}` | Status and progress |
| `POST` | `/api/compilations/{job_id}/cancel` | Stop a running export and delete its files |
| `GET` | `/api/download-folder` | Default save folder (`~/Downloads`) |
| `POST` | `/api/compilations/{job_id}/download` | Copy the MP4 to Downloads or `{"directory": "/full/path"}`, then delete the job folder. Local and desktop only; a hosted server returns `409` |
| `GET` | `/api/compilations/{job_id}/file` | Send the MP4 to the browser as an attachment. A full response marks the job `saved` and deletes the job folder 10 minutes later, so an interrupted download can be retried. A `Range` request does not start that countdown |
| `GET` | `/api/usage?ids=` | Compilation counts for up to 50 video ids |
| `GET` | `/api/logs` | Video history and compilation history |

`limit` defaults to 24 and cannot exceed 50. `offset` is how many playlist items to skip. The channel response includes `next_offset` and `has_more`.

A compilation body looks like this:

```json
{
  "output_4k": false,
  "clips": [
    {
      "video_id": "XXXXXXXXXXX",
      "title": "Intro",
      "start": "0:10",
      "end": "0:40",
      "order": 0
    }
  ]
}
```

`video_id` must be an 11-character YouTube id. `start` and `end` are `mm:ss` or `hh:mm:ss`, and `end` must be after `start`. An export needs 1 to 100 clips and at most 4 hours of kept time in total. Only one export runs at a time; starting another while one is running returns `409`. A cancelled export counts as running until its downloads and ffmpeg runs have actually stopped, which usually takes a few seconds.

Job statuses: `queued`, `downloading`, `concatenating`, `ready`, `saved`, `failed`, `cancelled`. While the status is `ready`, a local or desktop server sets `download_url` (save into a folder) and a hosted server sets `file_url` (download in the browser). A server counts as hosted when `VERCEL` or `K_SERVICE` (Cloud Run) is set. `saved_path` is present after a folder save and is the only remaining copy. A browser download ends in `saved` with no `saved_path`, and `file_url` stays available for 10 minutes.

## Environment variables

Backend (`backend/app/config.py` and the yt-dlp helpers):

| Variable | Default | Notes |
| --- | --- | --- |
| `CORS_ORIGINS` | `http://localhost:3000` | Comma-separated browser origins |
| `JOBS_DIR` | `backend/data/jobs` | Working files for an export. On Vercel the default is `/tmp/compcreator/jobs` because the bundle filesystem is read-only. The desktop app uses its Application Support jobs folder |
| `YTDLP_COOKIES_FILE` | unset | Path to a Netscape cookies file |
| `YTDLP_COOKIES` | unset | Cookie file contents, or the same contents in base64. A temp file is written with mode `0600` |
| `YTDLP_COOKIES_BROWSER` | unset | Browser to read cookies from. `none` skips browser cookies. The desktop app fills this in |
| `YTDLP_DENO` | discovered | Full path to Deno when cookies are used |
| `COMPCREATOR_PASSWORD` | unset | Shared password for the API. Required on a hosted server (`VERCEL` or `K_SERVICE` set), which refuses to start without it or with one shorter than 12 characters. Every `/api` request must send `Authorization: Bearer <password>`; `/health` stays open. The UI asks for it once per tab and keeps it in session storage until the tab closes. A finished video's `file_url` carries a token that unlocks only that job's file. The token is signed with a random key made at startup rather than with the password, so a leaked link cannot help anyone guess the password, and links stop working when the server restarts. After 5 wrong passwords or tokens in 15 minutes, a client (by IP, from the last `X-Forwarded-For` entry when hosted) gets `429` with `Retry-After` until the oldest failure is 15 minutes old. Requests that send no password do not count. Leave it unset for local use and the desktop app. Without a password, a local server answers only requests addressed to `localhost`, `127.0.0.1` or `[::1]`, which blocks DNS-rebinding pages; set a password to reach it from another address |
| `COMPCREATOR_DESKTOP` | unset | Set by the desktop launcher |

Frontend:

| Variable | Default | Notes |
| --- | --- | --- |
| `NEXT_PUBLIC_API_URL` | empty | Base URL of the API. Set it to the Cloud Run URL for the Vercel UI, and to `http://localhost:8000` for split local development. Leave it empty when the UI and API share an origin, as in the desktop app. The value is inlined at build time |
| `DESKTOP_EXPORT` | unset | `1` during `packaging/build.py`. Forces a static Next.js export and an empty API base so the window talks to the local server |

Copy `.env.example` to `.env` in the repository root for the backend list. The API reads that file on startup and does not override variables already set in the environment. For the frontend, put values in `frontend/.env.local`. The setup scripts create both files when they are missing.

Python dependencies are declared in `backend/pyproject.toml` and installed from `backend/requirements.txt` and `backend/requirements-dev.txt`. Those files carry the same pins, and `backend/tests/test_dependencies.py` fails if they drift. The pins are lower bounds so yt-dlp can update when YouTube changes. Frontend packages install from `frontend/package-lock.json` with `npm ci`.

## Local development

The API is at http://localhost:8000 and the UI at http://localhost:3000.

`ffmpeg` and `ffprobe` must be on `PATH` (`brew install ffmpeg` on macOS, `winget install Gyan.FFmpeg` on Windows). You also need Python 3.12 or newer and Node.js 20 or newer. yt-dlp comes from the Python environment, not from a separate binary. Deno 2.3 or newer is optional and is only required when YouTube cookies are configured.

### One command

From the repository root:

```bash
# macOS or Linux
./setup.sh          # create the virtualenv, install dependencies, write env files
./setup.sh dev      # set up, then start the API and the UI
./setup.sh lint     # Ruff, mypy, ESLint, API type freshness, and tsc
./setup.sh test     # Python unit tests
./setup.sh api-types  # regenerate frontend API types after changing a backend model

# Windows
setup.bat
setup.bat dev
setup.bat lint
setup.bat test
setup.bat api-types
```

`make setup`, `make dev`, `make lint`, `make test`, and `make api-types` run the same commands.

The frontend's API types are generated, not written by hand. `./setup.sh api-types` writes the backend's OpenAPI schema to `frontend/lib/api/openapi.json` and generates `frontend/lib/api/schema.gen.ts` from it; `frontend/lib/api/types.ts` gives those shapes the names the UI uses. Commit both generated files. A backend test and `./setup.sh lint` fail when they are out of date.

### Backend with a virtualenv

```bash
cd backend
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

Optional overrides:

```bash
CORS_ORIGINS=http://localhost:3000 JOBS_DIR=./data/jobs uvicorn app.main:app --reload --port 8000
```

### Backend with Docker Compose

The image listens on port 8080. Compose publishes that as host port 8000. Job files live inside the container and disappear when the container is removed.

```bash
docker compose up --build backend
```

Run the frontend on the host.

### Frontend

```bash
cd frontend
npm install
printf '%s\n' 'NEXT_PUBLIC_API_URL=http://localhost:8000' > .env.local
npm run dev
```

Open http://localhost:3000.

### Tests

From `backend/`, with the virtualenv active and `backend` on `PYTHONPATH`:

```bash
cd backend
PYTHONPATH=. python -m unittest discover -s tests
```

The suite covers timestamp parsing, channel URL normalization, channel listing, cookie selection, the stream-copy plan, delivery paths, cancellation, and the usage log. It does not download from YouTube or run ffmpeg.

### Smoke test

```bash
curl http://localhost:8000/health

curl -X POST "http://localhost:8000/api/channels?limit=5" \
  -H "Content-Type: application/json" \
  -d '{"url": "https://www.youtube.com/@SomeChannel"}'

curl -X POST http://localhost:8000/api/compilations \
  -H "Content-Type: application/json" \
  -d '{"clips": [{"video_id": "XXXXXXXXXXX", "title": "Intro", "start": "0:10", "end": "0:40", "order": 0}]}'

curl http://localhost:8000/api/compilations/<job_id>

curl -X POST http://localhost:8000/api/compilations/<job_id>/download \
  -H "Content-Type: application/json" \
  -d '{"directory": "/Users/you/Downloads"}'
```

## Desktop app

Installers from the latest build of `main` are on the [desktop-latest release](https://github.com/rgalpin5/CompilationCreator/releases/tag/desktop-latest):

- macOS: [CompCreator-mac.dmg](https://github.com/rgalpin5/CompilationCreator/releases/download/desktop-latest/CompCreator-mac.dmg)
- Windows: [CompCreator-windows.exe](https://github.com/rgalpin5/CompilationCreator/releases/download/desktop-latest/CompCreator-windows.exe)

Tagged versions have their own entries on the [releases page](https://github.com/rgalpin5/CompilationCreator/releases).

The window is the app. It starts a local API, serves the exported UI from that process, and saves finished videos to Downloads or to the folder you type. Working clips are deleted on save.

### macOS

1. Open `CompCreator-mac.dmg`.
2. Drag `CompCreator` onto Applications.
3. The first launch of an unsigned build: Control-click the app, choose Open, then Open again.
4. If the window does not open, read `desktop.log` in `~/Library/Application Support/CompCreator`.

### Windows

1. Double-click `CompCreator-windows.exe`. That file is the whole app.
2. If SmartScreen appears, choose More info, then Run anyway.
3. Windows 11 includes the WebView2 runtime the window needs. On Windows 10, install [WebView2](https://developer.microsoft.com/microsoft-edge/webview2/) if the window does not open.
4. The log is `desktop.log` in `%APPDATA%\CompCreator`.

### Rebuild

A Mac produces `dist/CompCreator-mac.dmg` only. Windows produces `dist/CompCreator-windows.exe` only. Each machine needs Node.js, npm, and Python 3.12. The script creates `build/venv`, installs `packaging/requirements-desktop.txt` (the backend requirements plus pywebview and PyInstaller), exports the UI, downloads ffmpeg, and writes the installer.

```bash
python packaging/build.py
```

The `Desktop packages` GitHub Actions workflow builds both installers on a manual run, a `v*` tag, or a push to `main` that changes `backend/`, `frontend/`, `packaging/`, or the workflow itself. It replaces the assets on the rolling `desktop-latest` release, and a `v*` tag also gets a release of its own. Installers are not committed to git. A weekly scheduled run rebuilds them when a newer yt-dlp is on PyPI than the one recorded in the release notes, so the published app keeps up with YouTube changes. The `Checks` workflow also runs weekly against the newest yt-dlp, and `./setup.sh` and `packaging/build.py` upgrade yt-dlp in existing virtualenvs.

## Deploy

The hosted setup is the API on Cloud Run and, optionally, the UI on Vercel. Vercel does not host the API: its functions stop long exports and cannot send a finished video of typical size.

### API on Cloud Run

Export work continues after the HTTP response, so CPU must stay allocated or the job freezes when the request ends. Keep the password and any cookies in Secret Manager rather than in plain environment variables.

```bash
cd backend
gcloud run deploy compcreator-api \
  --source . \
  --region us-central1 \
  --port 8080 \
  --memory 8Gi \
  --timeout 3600 \
  --no-cpu-throttling \
  --max-instances 1 \
  --allow-unauthenticated \
  --set-secrets "COMPCREATOR_PASSWORD=compcreator-password:latest" \
  --set-env-vars "CORS_ORIGINS=https://your-app.vercel.app"
```

Cloud Run sets `K_SERVICE`, which makes the API a hosted server: it refuses to start without `COMPCREATOR_PASSWORD`, sends finished videos to the browser through `/api/compilations/{job_id}/file`, does not save into server folders, and does not serve `/docs`, `/redoc` or `/openapi.json`. `--allow-unauthenticated` lets browsers reach the service; the password protects it. Add `YTDLP_COOKIES=<secret>:latest` to `--set-secrets` when YouTube requires a signed-in session, and never commit cookie files.

`--max-instances 1` keeps status polls and the download on the instance that holds the job. In-memory jobs and local MP4s do not survive a restart and are not shared across instances. Several origins need a custom gcloud delimiter because `--set-env-vars` splits on commas: `--set-env-vars "^;^CORS_ORIGINS=https://a.example,https://b.example"`. A later Cloud Storage signed-URL path is outlined in [docs/roadmap.md](docs/roadmap.md) and is not built.

### UI on Vercel

`vercel.json` deploys only the Next.js frontend (`frontend/`). In the Vercel project settings, set `NEXT_PUBLIC_API_URL` to the Cloud Run URL and redeploy; the value is inlined at build time. List the Vercel origin in the API's `CORS_ORIGINS`. The UI asks for the API password once per tab and keeps it until the tab closes.

## Not wired up

[docs/roadmap.md](docs/roadmap.md) outlines features that are not built:

- Cloud Storage delivery: upload a finished MP4 and return a signed URL.
- YouTube upload: upload a finished compilation with the YouTube Data API.
- Autopilot: scheduled channel scans that suggest compilation ideas.

`max_video_height` in `backend/app/youtube/formats.py` is also unused by the current routes.
