import { formatSeconds, parseTime, setTrimPoint } from "@/lib/time";

export type TrimPatch = { start?: string; end?: string };

/**
 * The clip's start and end in seconds. A blank or unreadable end becomes one
 * second after the start when the video length is known, else one minute.
 */
export function clipBounds(
  start: string,
  end: string,
  duration: number | null,
): { startSec: number; endSec: number } {
  const startSec = parseTime(start) ?? 0;
  const endSec =
    parseTime(end) ??
    (duration != null ? Math.min(Math.floor(duration), startSec + 1) : startSec + 60);
  return { startSec, endSec };
}

/**
 * Move one side of the clip to ``point``. ``patch`` holds only the fields that
 * changed, and is null when neither did.
 */
export function trimTo(
  startSec: number,
  endSec: number,
  which: "start" | "end",
  point: number,
  duration: number | null,
): { next: { start: number; end: number }; patch: TrimPatch | null } {
  const next = setTrimPoint(startSec, endSec, which, point, duration);
  const patch: TrimPatch = {};
  if (next.start !== startSec) patch.start = formatSeconds(next.start);
  if (next.end !== endSec) patch.end = formatSeconds(next.end);
  const changed = patch.start !== undefined || patch.end !== undefined;
  return { next, patch: changed ? patch : null };
}
