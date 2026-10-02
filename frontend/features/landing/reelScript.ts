/**
 * The hero edit as a script. One clock drives everything: the playhead visits each intro and
 * outro, a razor mark lands, the cut falls away and the lane ripples shut. Then the finished
 * reel plays back and renders. All numbers are derived from the same segment lengths, so the
 * runtime readout and ruler are honest at every frame.
 */
export type Clip = { intro: number; body: number; outro: number; label: string };

// Lengths are relative units of source footage.
export const CLIPS: Clip[] = [
  { intro: 4, body: 16, outro: 3, label: "Goals" },
  { intro: 6, body: 9, outro: 3, label: "Rally #12" },
  { intro: 3, body: 18, outro: 5, label: "Recap" },
  { intro: 5, body: 6, outro: 3, label: "Fails" },
  { intro: 4, body: 8, outro: 3, label: "Top 10" },
];

export type Segment = { clip: number; kind: "intro" | "body" | "outro"; weight: number; cut: number };

/** Segments left to right. `cut` is the index in the razor order, or -1 for kept footage. */
export const SEGMENTS: Segment[] = CLIPS.flatMap((clip, i) => [
  { clip: i, kind: "intro" as const, weight: clip.intro, cut: i * 2 },
  { clip: i, kind: "body" as const, weight: clip.body, cut: -1 },
  { clip: i, kind: "outro" as const, weight: clip.outro, cut: i * 2 + 1 },
]);

const CUT_COUNT = CLIPS.length * 2;
const RAW_UNITS = SEGMENTS.reduce((sum, segment) => sum + segment.weight, 0);
/** The raw footage runs 1:12:40. */
export const RAW_SECONDS = 4360;

const START = 0.7;
/** Seconds spent on each razor stop: a slow first cut so it reads, then the edit picks up speed. */
const STOPS = [1.2, 0.95, 0.8, 0.68, 0.58, 0.5, 0.44, 0.4, 0.36, 0.34];
const STARTS = STOPS.map((_, k) => START + STOPS.slice(0, k).reduce((sum, d) => sum + d, 0));
const END_CUTS = START + STOPS.reduce((sum, d) => sum + d, 0);
const REWIND_FOR = 0.4;
const PLAY_FROM = END_CUTS + 0.5;
const PLAY_FOR = 2.4;
const RENDER_FOR = 1.3;
export const LOOP_SECONDS = PLAY_FROM + PLAY_FOR + RENDER_FOR + 1.6;
/** A time at which the edit is finished and rendered, for reduced motion. */
export const FINAL_TIME = PLAY_FROM + PLAY_FOR + RENDER_FOR + 0.2;

const ease = (x: number) => (x < 0.5 ? 4 * x * x * x : 1 - (-2 * x + 2) ** 3 / 2);
const clamp01 = (x: number) => Math.min(1, Math.max(0, x));

export type Frame = {
  /** Lane flex-grow for each segment. */
  grow: number[];
  /** How far each segment's cut has progressed, 0 to 1. */
  progress: number[];
  /** Playhead position along the lane, 0 to 1. */
  head: number;
  /** Razor mark: opacity and which edge. */
  razor: { opacity: number; label: string };
  runtime: number;
  cutAway: number;
  render: number;
  stage: "trim" | "play" | "render" | "done";
};

function cutProgress(k: number, t: number): number {
  const dur = STOPS[k] ?? 0.4;
  const from = (STARTS[k] ?? START) + dur * 0.48;
  return ease(clamp01((t - from) / (dur * 0.46)));
}

function layout(progress: number[]): { grow: number[]; total: number } {
  const grow = SEGMENTS.map((segment) =>
    segment.cut < 0 ? segment.weight : segment.weight * (1 - (progress[segment.cut] ?? 0)),
  );
  return { grow, total: grow.reduce((sum, value) => sum + value, 0) };
}

/** Position (0 to 1) of the in point (right edge of an intro) or out point (left edge of an outro). */
function edge(k: number, progress: number[]): number {
  const { grow, total } = layout(progress);
  const index = SEGMENTS.findIndex((segment) => segment.cut === k);
  const isIntro = SEGMENTS[index]?.kind === "intro";
  let sum = 0;
  for (let i = 0; i < (isIntro ? index + 1 : index); i += 1) sum += grow[i] ?? 0;
  return sum / total;
}

function progressAfter(done: number): number[] {
  return Array.from({ length: CUT_COUNT }, (_, k) => (k < done ? 1 : 0));
}

export function frameAt(t: number): Frame {
  const progress = Array.from({ length: CUT_COUNT }, (_, k) => cutProgress(k, t));
  const { grow, total } = layout(progress);

  let head = 0;
  let razorOpacity = 0;
  let razorLabel = "IN";
  let stage: Frame["stage"] = "trim";

  if (t >= START && t < END_CUTS) {
    let k = STARTS.length - 1;
    while (k > 0 && t < (STARTS[k] ?? 0)) k -= 1;
    const dur = STOPS[k] ?? 0.4;
    const u = t - (STARTS[k] ?? START);
    razorLabel = k % 2 === 0 ? "IN" : "OUT";
    const glide = dur * 0.42;
    if (u < glide) {
      const from = k === 0 ? 0 : edge(k - 1, progressAfter(k));
      const to = edge(k, progressAfter(k));
      head = from + (to - from) * ease(u / glide);
    } else {
      head = edge(k, progress);
    }
    // The razor lands as the playhead arrives and holds for a beat while the cut drops out.
    razorOpacity = u >= glide - 0.03 ? clamp01(1 - (u - glide) / (dur * 0.9)) : 0;
  } else if (t >= END_CUTS) {
    const rewind = ease(clamp01((t - END_CUTS) / REWIND_FOR));
    const play = clamp01((t - PLAY_FROM) / PLAY_FOR);
    head = t < PLAY_FROM ? 1 - rewind : play;
    stage = t < PLAY_FROM + PLAY_FOR ? "play" : t < PLAY_FROM + PLAY_FOR + RENDER_FOR ? "render" : "done";
  }

  const runtime = Math.round((RAW_SECONDS * total) / RAW_UNITS);
  const render = clamp01((t - PLAY_FROM - PLAY_FOR) / RENDER_FOR);
  return {
    grow,
    progress: SEGMENTS.map((segment) => (segment.cut < 0 ? 0 : (progress[segment.cut] ?? 0))),
    head,
    razor: { opacity: razorOpacity, label: razorLabel },
    runtime,
    cutAway: RAW_SECONDS - runtime,
    render,
    stage,
  };
}
