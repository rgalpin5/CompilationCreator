# CompCreator

A personal tool for building mega compilations from a YouTube channel. Paste a channel URL, pick 4–8 videos of about 20–30 minutes each, trim them, reorder them, and export one long mp4.

YouTube's Terms of Service restrict downloading content. Use this only for videos you own or otherwise have the right to download and reuse.

This is for personal use. There is no authentication.

## Desktop app

Install the build for your computer and open it. The window is the app. It does not use a shared YouTube login: downloads use the browser signed in on that machine. Finished compilations are kept in the app's folder on that computer, and the Download button in the window saves a copy as well.

The first time a download runs, macOS may ask for Keychain access so the app can read that browser's YouTube cookies. Allow it. Chrome is used when it is installed, then Brave, Edge, Firefox, and Safari. Set `YTDLP_COOKIES_BROWSER` to one of those names before launching if you want a different one, or `none` to skip browser cookies.

### macOS

1. Unzip `CompCreator-mac.zip`.
2. Move `CompCreator.app` into Applications.
3. The first time, Control-click the app and choose Open, then Open again. macOS blocks an unsigned app on a double-click.
4. Finished compilations are in `~/Library/Application Support/CompCreator/jobs`. If the window fails to open, the log is `desktop.log` in that same CompCreator folder.

### Windows

1. Unzip `CompCreator-windows.zip`.
2. Open the `CompCreator` folder and double-click `CompCreator.exe`. Leave the folder intact. The exe needs the files next to it.
3. If Windows SmartScreen appears, choose More info, then Run anyway.
4. Windows 11 already includes the WebView2 runtime the window needs. On Windows 10, install [WebView2](https://developer.microsoft.com/microsoft-edge/webview2/) if the window does not open.
5. Finished compilations are in `%APPDATA%\CompCreator\jobs`. The log is `desktop.log` in that same CompCreator folder.

## Layout

- `backend/`: FastAPI app (`app.main:app`). Uses yt-dlp to list and download videos and ffmpeg to trim and concatenate.
- `frontend/`: Next.js (App Router) UI.
- `packaging/`: builds the macOS and Windows apps.
- `docker-compose.yml`: runs the backend only.

## Limits

- Videos per compilation: up to 8. The editor is aimed at 4–8.
- Each video: at most 35 minutes (so a video that runs a little past 30:00 still fits).
- Whole compilation: at most 4 hours 40 minutes (eight 35-minute videos).
- Adding a video fills the end time with its full length when that length is known, otherwise 30:00.
- An export downloads its clips together, then joins matching clips by stream copy without re-encoding. Only a clip whose picture or audio track does not match is re-encoded, and only that track. A 3–4 hour compilation needs substantial disk space and can take a long time. Keep the page open while it runs.
- Channel listing: 24 videos by default, 50 maximum (`?limit=` on `POST /api/channels`).

## API

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/health` | Health check |
| POST | `/api/channels` | List recent videos for a channel URL |
| POST | `/api/compilations` | Start an export job (returns 202 with a job id) |
| GET | `/api/compilations/{job_id}` | Job status and progress |
| GET | `/api/compilations/{job_id}/download` | Download the finished mp4 |

Export is asynchronous: `POST /api/compilations` returns immediately and the compilation runs in a background task. Poll the status endpoint until `status` is `ready`, then fetch `download_url`.

## Environment variables

Backend:

| Variable | Default | Notes |
| --- | --- | --- |
| `CORS_ORIGINS` | `http://localhost:3000` | Comma-separated list of allowed origins |
| `JOBS_DIR` | `backend/data/jobs` | Working files and finished mp4s |

Frontend:

| Variable | Default | Notes |
| --- | --- | --- |
| `NEXT_PUBLIC_API_URL` | `http://localhost:8000` | Base URL of the backend. Inlined at build time. |

See `.env.example` for a copy-paste starting point. For the frontend, put values in `frontend/.env.local`.

## Build the desktop app

Build on the operating system you want to ship. A Mac produces the Mac zip only. Windows produces the Windows zip only. GitHub Actions workflow `Desktop packages` builds both when you run it by hand or push a `v*` tag. Artifacts are `CompCreator-mac.zip` and `CompCreator-windows.zip`.

```bash
python packaging/build.py
```

Needs Node.js, npm, and Python 3.12. The script installs the desktop Python packages into `build/venv`, exports the UI, downloads ffmpeg, and writes the zip under `dist/`.

## Local run

The backend is reachable at http://localhost:8000 and the frontend at http://localhost:3000 in both options.

### Option A: Python venv

A virtualenv already exists at `backend/.venv`. For non-Docker runs, `ffmpeg` must be on your `PATH` (for example `brew install ffmpeg`). Downloads use the `yt-dlp` package inside that virtualenv, not a separately installed binary.

```bash
cd backend
source .venv/bin/activate
pip install -r requirements.txt   # if dependencies are not installed yet
uvicorn app.main:app --reload --port 8000
```

Optional overrides:

```bash
CORS_ORIGINS=http://localhost:3000 JOBS_DIR=./data/jobs uvicorn app.main:app --reload --port 8000
```

### Option B: Docker Compose (backend only)

The image is based on `python:3.12-slim`, installs ffmpeg via apt and yt-dlp via pip, and listens on port 8080. Compose maps host port 8000 to container port 8080.

```bash
docker compose up --build backend
```

Jobs are written inside the container and are lost when the container is removed.

Then run the frontend on the host as described below.

### Frontend

```bash
cd frontend
npm install
echo "NEXT_PUBLIC_API_URL=http://localhost:8000" > .env.local   # optional; this is the default
npm run dev
```

Open http://localhost:3000.

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
curl -o compilation.mp4 http://localhost:8000/api/compilations/<job_id>/download
```

## Deploy

### Backend on Cloud Run

Deploy from the `backend/` directory using its Dockerfile:

```bash
cd backend
gcloud run deploy compcreator-api \
  --source . \
  --region us-central1 \
  --port 8080 \
  --memory 8Gi \
  --timeout 3600 \
  --no-cpu-throttling \
  --allow-unauthenticated \
  --set-env-vars "CORS_ORIGINS=https://your-app.vercel.app"
```

Notes:

- `--no-cpu-throttling` (CPU always allocated) is required. Export runs in a background task after the HTTP response is sent, and Cloud Run freezes CPU once a request ends unless CPU is always allocated. Without this flag, compilations stall and never finish.
- `--allow-unauthenticated` is for personal use only; there is no auth in the app.
- To allow several origins (for example production plus a preview URL), pass a comma-separated list. Because gcloud also splits `--set-env-vars` on commas, use a custom delimiter: `--set-env-vars "^;^CORS_ORIGINS=https://a.vercel.app,https://b.vercel.app"`.
- Consider `--max-instances 1` so status polls and downloads hit the same instance that ran the job.
- Job state is held in memory and finished mp4s are stored on the instance's local disk. Neither survives an instance restart, scale-down, or redeploy, and they are not shared across instances. Serving downloads from Google Cloud Storage via signed URLs is stubbed in `backend/app/stubs/gcs_download.py` and not wired up.

### Frontend on Vercel

- Import the repo and set the project Root Directory to `frontend/`.
- Framework preset: Next.js. Do not set a custom `output` mode in `next.config.ts`.
- Set `NEXT_PUBLIC_API_URL` to the Cloud Run service URL (for example `https://compcreator-api-xxxxx-uc.a.run.app`). Redeploy after changing it, since it is inlined at build time.
- Make sure the Vercel origin is listed in the backend's `CORS_ORIGINS`.

## Stubs not wired up

These modules exist as placeholders and are not called by the app:

- `backend/app/stubs/gcs_download.py`: upload finished mp4s to GCS and return signed URLs.
- `backend/app/stubs/youtube_upload.py`: upload a finished compilation via the YouTube Data API (OAuth plus resumable upload).
- `backend/app/stubs/autopilot.py`: scheduled scans of a channel watchlist to suggest compilation ideas.
