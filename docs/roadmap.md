# Roadmap: features not built

These are outlines only. None of them is implemented, and nothing in the app refers to them. They used to live as commented-out modules in `backend/app/stubs/`.

## Serve finished videos from Cloud Storage

The hosted API sends the finished `compilation.mp4` from the instance disk. On Cloud Run that file disappears with the instance. A later version can:

1. Upload the MP4 to `gs://$GCS_BUCKET/jobs/{job_id}/compilation.mp4`.
2. Return a short-lived V4 signed URL as the download link.
3. Delete the local file.

This needs a service account with `storage.objects.create`.

Sketch: `signed_download_url(job_id: str, local_path: str) -> str`.

## Upload a compilation to YouTube

1. OAuth consent for scope `https://www.googleapis.com/auth/youtube.upload`.
   - Store refresh tokens outside the repo (Secret Manager on GCP).
   - Redirect URI: `{PUBLIC_API_URL}/api/youtube/oauth/callback`.
2. `POST /api/youtube/upload { job_id, title, description, privacyStatus }`.
   - Read the finished `compilation.mp4` for that job.
   - Start a resumable upload:
     `POST https://www.googleapis.com/upload/youtube/v3/videos?uploadType=resumable&part=snippet,status`
   - `PUT` the file bytes to the `Location` header, in chunks.
3. Return the new video id to the UI.

Do not enable this until the user has a Google Cloud OAuth client and has explicitly agreed to upload their own compilations.

Sketch: `upload_compilation(file_path: str, title: str, description: str, privacy: str) -> str`.

## Autopilot / idea scout

- A Cloud Scheduler job calls `POST /internal/autopilot/scan` on a cron.
- The handler reads a saved watchlist of channel URLs.
- For each channel it lists recent uploads, reusing the channel listing in `backend/app/youtube/listing.py`.
- A scorer (keywords, view velocity, duration) writes "ideas" to storage.
- A separate worker could turn an accepted idea into a compilation job.

Keep this off the request path that serves the manual editor. Scanning channels on a timer needs its own quota, logging, and an explicit opt-in.

Sketch: `scan_watchlist(channel_urls: list[str]) -> list[dict]`.
