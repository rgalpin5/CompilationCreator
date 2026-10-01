import { API_BASE, request } from "./client";
import type { ClipPayload, Job } from "./types";

/** Absolute link for a job's ``file_url``, which the browser downloads directly. */
export function compilationFileHref(fileUrl: string): string {
  return `${API_BASE}${fileUrl}`;
}

/** Queue an export and return the new job. */
export function createCompilation(clips: ClipPayload[], output4k = false): Promise<Job> {
  return request<Job>("/api/compilations", {
    method: "POST",
    body: JSON.stringify({ clips, output_4k: output4k }),
  });
}

/** Read the latest status of an export. */
export function getCompilation(id: string): Promise<Job> {
  return request<Job>(`/api/compilations/${encodeURIComponent(id)}`);
}

/** Stop an export that is still running. */
export function cancelCompilation(id: string): Promise<Job> {
  return request<Job>(`/api/compilations/${encodeURIComponent(id)}/cancel`, {
    method: "POST",
  });
}

/** The folder the server uses when the save field is left blank. */
export function fetchDownloadFolder(): Promise<string> {
  return request<{ path: string }>("/api/download-folder").then((data) => data.path);
}

/** Copy a finished export into ``directory``, or into Downloads when it is blank. */
export function saveCompilation(id: string, directory: string): Promise<Job> {
  return request<Job>(`/api/compilations/${encodeURIComponent(id)}/download`, {
    method: "POST",
    body: JSON.stringify({ directory: directory.trim() || null }),
  });
}
