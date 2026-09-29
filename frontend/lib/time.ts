export const TARGET_MIN_CLIPS = 4;
export const MAX_CLIPS = 8;
export const MAX_CLIP_SECONDS = 35 * 60;
export const MAX_TOTAL_SECONDS = MAX_CLIPS * MAX_CLIP_SECONDS;
export const DEFAULT_CLIP_SECONDS = 30 * 60;

const MM_SS = /^(\d{1,2}):([0-5]\d)$/;
const HH_MM_SS = /^(\d+):([0-5]\d):([0-5]\d)$/;

/** Parses mm:ss or hh:mm:ss (minutes and seconds 0-59). Returns null if invalid. */
export function parseTime(value: string): number | null {
  const v = value.trim();
  let m = HH_MM_SS.exec(v);
  if (m) return Number(m[1]) * 3600 + Number(m[2]) * 60 + Number(m[3]);
  m = MM_SS.exec(v);
  if (m) {
    const minutes = Number(m[1]);
    if (minutes > 59) return null;
    return minutes * 60 + Number(m[2]);
  }
  return null;
}

export function formatSeconds(total: number): string {
  const s = Math.max(0, Math.floor(total));
  const h = Math.floor(s / 3600);
  const m = Math.floor((s % 3600) / 60);
  const sec = s % 60;
  const pad = (n: number) => String(n).padStart(2, "0");
  return h > 0 ? `${h}:${pad(m)}:${pad(sec)}` : `${pad(m)}:${pad(sec)}`;
}

export type TimedClip = { title: string; start: string; end: string };

/** Returns an error message, or null if the timeline is valid. */
export function validateClips(clips: TimedClip[]): string | null {
  if (clips.length === 0) return "Add at least one clip to the timeline.";
  if (clips.length > MAX_CLIPS)
    return `A compilation can have at most ${MAX_CLIPS} clips.`;

  let total = 0;
  for (const [i, clip] of clips.entries()) {
    const label = `Clip ${i + 1} ("${clip.title}")`;
    const start = parseTime(clip.start);
    const end = parseTime(clip.end);
    if (start === null)
      return `${label}: start "${clip.start}" must be mm:ss or hh:mm:ss.`;
    if (end === null)
      return `${label}: end "${clip.end}" must be mm:ss or hh:mm:ss.`;
    if (end <= start) return `${label}: end must be after start.`;
    const length = end - start;
    if (length > MAX_CLIP_SECONDS)
      return `${label}: each video can be at most 35:00 (this one is ${formatSeconds(length)}).`;
    total += length;
  }

  if (total > MAX_TOTAL_SECONDS)
    return `Total length is ${formatSeconds(total)}; the maximum is 4:40:00.`;
  return null;
}

/** End time for a newly added video: the full length, capped at 35:00. */
export function defaultEnd(durationSeconds: number | null): string {
  const seconds =
    durationSeconds && durationSeconds > 0
      ? Math.min(Math.floor(durationSeconds), MAX_CLIP_SECONDS)
      : DEFAULT_CLIP_SECONDS;
  return formatSeconds(seconds);
}
