export type Video = {
  video_id: string;
  title: string;
  thumbnail: string | null;
  duration_seconds: number | null;
  url: string;
  compilation_count: number;
  channel?: string | null;
  view_count?: number | null;
};

export type ChannelPage = {
  videos: Video[];
  next_offset: number;
  has_more: boolean;
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
  | "saved"
  | "failed"
  | "cancelled";

export type Job = {
  id: string;
  status: JobStatus;
  progress: string | null;
  error: string | null;
  download_url: string | null;
  saved_path: string | null;
};
