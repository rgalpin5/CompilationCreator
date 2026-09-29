"""Stub for serving finished compilations from Cloud Storage.

The current download route streams compilation.mp4 from the instance disk.
On Cloud Run that file disappears with the instance. A later version can:

1. Upload the mp4 to gs://$GCS_BUCKET/jobs/{job_id}/compilation.mp4
2. Return a V4 signed URL (short expiry) as download_url
3. Delete the local file

Not wired up. Requires a service account with storage.objects.create.
"""


# def signed_download_url(job_id: str, local_path: str) -> str:
#     raise NotImplementedError("GCS signed URLs are not implemented")
