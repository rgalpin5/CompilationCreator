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

/** Format a non-negative duration as ``mm:ss`` or ``h:mm:ss``. */
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

  for (const [i, clip] of clips.entries()) {
    const label = `Clip ${i + 1} ("${clip.title}")`;
    const start = parseTime(clip.start);
    const end = parseTime(clip.end);
    if (start === null)
      return `${label}: start "${clip.start}" must be mm:ss or hh:mm:ss.`;
    if (end === null)
      return `${label}: end "${clip.end}" must be mm:ss or hh:mm:ss.`;
    if (end <= start) return `${label}: end must be after start.`;
  }

  return null;
}

/** End time for a newly added video: the full length when it is known. */
export function defaultEnd(durationSeconds: number | null): string {
  const seconds =
    durationSeconds && durationSeconds > 0
      ? Math.floor(durationSeconds)
      : DEFAULT_CLIP_SECONDS;
  return formatSeconds(seconds);
}

/**
 * Move the start or the end to a point on the video.
 * The kept range stays at least one second, and neither side can pass the video length.
 */
export function setTrimPoint(
  startSec: number,
  endSec: number,
  which: "start" | "end",
  point: number,
  duration: number | null,
): { start: number; end: number } {
  const max = duration != null && duration > 1 ? Math.floor(duration) : null;
  const rounded = Math.max(0, Math.round(point));

  if (which === "start") {
    let start = max == null ? rounded : Math.min(rounded, max - 1);
    start = Math.min(start, Math.max(0, endSec - 1));
    return { start, end: endSec };
  }

  let end = max == null ? rounded : Math.min(rounded, max);
  end = Math.max(end, startSec + 1);
  return { start: startSec, end };
}
