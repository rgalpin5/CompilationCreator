"""Stub for a later YouTube Data API upload.

Not imported by any route. Outline only:

1. OAuth consent for scope https://www.googleapis.com/auth/youtube.upload
   - Store refresh tokens outside the repo (Secret Manager on GCP).
   - Redirect URI: {PUBLIC_API_URL}/api/youtube/oauth/callback
2. POST /api/youtube/upload { job_id, title, description, privacyStatus }
   - Read the finished compilation.mp4 for that job.
   - Start a resumable upload:
     POST https://www.googleapis.com/upload/youtube/v3/videos?uploadType=resumable&part=snippet,status
   - PUT the file bytes to the Location header, chunked.
3. Return the new video id to the UI.

Do not enable this until the user has a Google Cloud OAuth client and
explicit consent to upload their own compilations.
"""


# def upload_compilation(file_path: str, title: str, description: str, privacy: str) -> str:
#     raise NotImplementedError("YouTube upload is not implemented")
