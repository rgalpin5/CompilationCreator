/** The page is one timeline of about four minutes. Section markers, the ruler and the transport share these. */
export const PAGE_SECONDS = 240;

export const SECTION_TIMES = {
  intro: 0,
  how: 60,
  access: 180,
  end: PAGE_SECONDS,
} as const;

/** The pinned multitrack runs from here to here; its own ruler uses the same seconds. */
export const SEQUENCE_TIMES = { start: 70, end: 130 } as const;

/** Height of the sticky site header; sections land just below it. */
export const HEADER_PX = 56;

export function formatTimecode(totalSeconds: number): string {
  const whole = Math.max(0, Math.round(totalSeconds));
  const hours = Math.floor(whole / 3600);
  const minutes = Math.floor((whole % 3600) / 60);
  const seconds = whole % 60;
  return [hours, minutes, seconds].map((part) => String(part).padStart(2, "0")).join(":");
}

export const TC = {
  intro: formatTimecode(SECTION_TIMES.intro),
  how: formatTimecode(SECTION_TIMES.how),
  access: formatTimecode(SECTION_TIMES.access),
};

export type Anchors = {
  /** Scroll offsets at which each point sits at the top of the viewport. */
  how: number;
  seqStart: number;
  seqEnd: number;
  access: number;
  max: number;
};

/**
 * Maps a scroll offset to a time on the page timeline. Each anchor is the scroll offset at which
 * a section (or the pinned sequence) arrives, so the readout shows exactly its timecode then. The
 * anchors are forced to ascend rather than clamped to page fractions, so a short page keeps every
 * guarantee. After the last anchor the playhead keeps the speed of the stretch before it, so it
 * never visibly speeds up; the timeline therefore ends wherever that speed reaches the page
 * bottom, and `end` reports it so the transport can scale its bar to fit.
 */
export function timelineAt(scrollY: number, anchors: Anchors): { time: number; end: number } {
  const max = Math.max(1, anchors.max);
  const y = Math.min(Math.max(scrollY, 0), max);

  let previous = 0;
  const ascend = (value: number): number => {
    previous = Math.max(value, previous + 1);
    return previous;
  };
  const points: [number, number][] = [
    [0, SECTION_TIMES.intro],
    [ascend(anchors.how), SECTION_TIMES.how],
    [ascend(anchors.seqStart), SEQUENCE_TIMES.start],
    [ascend(anchors.seqEnd), SEQUENCE_TIMES.end],
    [ascend(anchors.access), SECTION_TIMES.access],
  ];

  const [accessY] = points[4] ?? [max, 0];
  const [seqEndY] = points[3] ?? [0, 0];
  const rate = (SECTION_TIMES.access - SEQUENCE_TIMES.end) / Math.max(1, accessY - seqEndY);
  const end = Math.max(SECTION_TIMES.access + 15, SECTION_TIMES.access + (max - accessY) * rate);

  for (let i = 1; i < points.length; i += 1) {
    const [y1, t1] = points[i] ?? [max, SECTION_TIMES.access];
    const [y0, t0] = points[i - 1] ?? [0, 0];
    if (y <= y1) return { time: t0 + ((y - y0) / (y1 - y0)) * (t1 - t0), end };
  }
  return { time: Math.min(end, SECTION_TIMES.access + (y - accessY) * rate), end };
}

function offsetOf(id: string): number {
  const element = document.getElementById(id);
  if (!element) return 0;
  return element.getBoundingClientRect().top + window.scrollY - HEADER_PX;
}

/** Reads the live anchors from the DOM. Call from the browser only. */
export function readAnchors(): Anchors {
  const max = document.documentElement.scrollHeight - window.innerHeight;
  const sequence = document.getElementById("sequence");
  const pin = sequence?.querySelector<HTMLElement>("[data-pin]") ?? null;
  const pinned = pin != null && pin.offsetHeight > 0;

  let seqStart = offsetOf("sequence");
  let seqEnd = seqStart + 1;
  if (sequence && pin && pinned) {
    const stage = pin.firstElementChild as HTMLElement | null;
    seqEnd = seqStart + pin.offsetHeight - (stage?.offsetHeight ?? 0);
  } else if (sequence) {
    seqEnd = sequence.getBoundingClientRect().bottom + window.scrollY - window.innerHeight;
  }
  seqEnd = Math.max(seqEnd, seqStart + 1);
  seqStart = Math.max(seqStart, 0);

  return { how: offsetOf("how"), seqStart, seqEnd, access: offsetOf("get-access"), max };
}
