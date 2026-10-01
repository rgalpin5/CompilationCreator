export type TimelineClip = {
  video_id: string;
  title: string;
  start: string;
  end: string;
  channel?: string | null;
  view_count?: number | null;
  duration_seconds?: number | null;
  thumbnail?: string | null;
};
