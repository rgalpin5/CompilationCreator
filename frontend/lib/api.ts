// Same origin by default. Vercel rewrites `/api/*` and `/health` to the
// backend service, and the API already mounts its routes under `/api`.
// Set NEXT_PUBLIC_API_URL only when the API is on another origin, such as
// `npm run dev` against uvicorn on port 8000. A service binding cannot
// supply this value: every call below runs in the browser.
const configured = process.env.NEXT_PUBLIC_API_URL?.trim().replace(/\/+$/, "");
export const API_BASE = configured ? configured : "";

export type Video = {
  video_id: string;
  title: string;
  thumbnail: string;
  duration_seconds: number | null;
  url: string;
  compilation_count: number;
  channel?: string | null;
  view_count?: number | null;
};

export type ClipPayload = {
  video_id: string;
  title: string;
  start: string;
  end: string;
  order: number;
  channel?: string | null;
  view_count?: number | null;
  duration_seconds?: number | null;
  thumbnail?: string | null;
};

export type VideoLog = {
  video_id: string;
  title: string;
  channel: string | null;
  view_count: number | null;
  duration_seconds: number | null;
  thumbnail: string | null;
  last_used: string | null;
  count: number;
};

export type CompilationLog = {
  name: string;
  made: string;
  clips: number;
  duration_seconds: number;
};

export type Logs = {
  videos: VideoLog[];
  compilations: CompilationLog[];
};

export type JobStatus =
  | "queued"
  | "downloading"
  | "concatenating"
  | "ready"
  | "failed"
  | "cancelled";

export type Job = {
  id: string;
  status: JobStatus;
  progress: string | null;
  error: string | null;
  download_url: string | null;
};

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let res: Response;
  try {
    res = await fetch(`${API_BASE}${path}`, {
      ...init,
      headers: { "Content-Type": "application/json", ...init?.headers },
    });
  } catch {
    throw new Error(
      API_BASE ? `Could not reach the API at ${API_BASE}` : "Could not reach the API",
    );
  }

  const body = await res.json().catch(() => null);
  if (!res.ok) {
    const detail = body?.detail;
    const message =
      typeof detail === "string"
        ? detail
        : detail
          ? JSON.stringify(detail)
          : `Request failed with status ${res.status}`;
    throw new Error(message);
  }
  return body as T;
}

export async function fetchChannelVideos(
  url: string,
  limit = 24,
): Promise<Video[]> {
  const data = await request<{ videos: Video[] }>(
    `/api/channels?limit=${limit}`,
    { method: "POST", body: JSON.stringify({ url }) },
  );
  return data.videos;
}

export function createCompilation(
  clips: ClipPayload[],
  output4k = false,
): Promise<Job> {
  return request<Job>("/api/compilations", {
    method: "POST",
    body: JSON.stringify({ clips, output_4k: output4k }),
  });
}

export function getCompilation(id: string): Promise<Job> {
  return request<Job>(`/api/compilations/${encodeURIComponent(id)}`);
}

export function cancelCompilation(id: string): Promise<Job> {
  return request<Job>(`/api/compilations/${encodeURIComponent(id)}/cancel`, {
    method: "POST",
  });
}

export function downloadHref(downloadUrl: string): string {
  return `${API_BASE}${downloadUrl}`;
}

export function fetchLogs(): Promise<Logs> {
  return request<Logs>("/api/logs");
}

export async function fetchUsage(ids: string[]): Promise<Record<string, number>> {
  if (ids.length === 0) return {};
  const data = await request<{ counts: Record<string, number> }>(
    `/api/usage?ids=${ids.map((id) => encodeURIComponent(id)).join(",")}`,
  );
  return data.counts;
}
