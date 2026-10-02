"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { PauseIcon, PlayIcon } from "@/components/icons";
import { cn } from "@/lib/utils";
import Brackets from "./Brackets";
import { CLIPS, FINAL_TIME, frameAt, LOOP_SECONDS, SEGMENTS, type Frame } from "./reelScript";
import { formatTimecode } from "./timeline";

// Fixed bar heights so the waveform renders the same on server and client.
const WAVE = [4, 7, 5, 9, 6, 3, 8, 10, 6, 4, 7, 9, 5, 3, 6, 8, 4, 7, 10, 5, 6, 9, 4, 3, 7, 8, 5, 6, 9, 4];
// Labels sit on major ticks (every 12.5%), so they never slide against the ruler.
const RULER_STOPS = [0, 0.25, 0.5, 0.75];

type Clock = { t: number; fade: number };

/**
 * Drives the script with one clock; reduced motion shows the finished edit. Pausing freezes the
 * frame, and playing again carries on from it.
 */
function useReelClock(paused: boolean): Clock {
  const [clock, setClock] = useState<Clock>({ t: 0, fade: 1 });
  const elapsedRef = useRef(0);

  useEffect(() => {
    let raf = 0;
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
      raf = requestAnimationFrame(() => setClock({ t: FINAL_TIME, fade: 1 }));
      return () => cancelAnimationFrame(raf);
    }
    if (paused) return;
    const origin = performance.now() - elapsedRef.current * 1000;
    function tick(now: number) {
      const elapsed = (now - origin) / 1000;
      elapsedRef.current = elapsed;
      const t = elapsed % LOOP_SECONDS;
      const looped = elapsed >= LOOP_SECONDS;
      let fade = 1;
      if (looped && t < 0.35) fade = t / 0.35;
      else if (t > LOOP_SECONDS - 0.35) fade = (LOOP_SECONDS - t) / 0.35;
      setClock({ t, fade });
      raf = requestAnimationFrame(tick);
    }
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [paused]);

  return clock;
}

/** The product in one picture: a scripted edit where the playhead razors each intro and outro. */
export default function HeroReel() {
  // Looping motion needs a way to stop it (WCAG 2.2.2), whatever the OS motion setting.
  const [paused, setPaused] = useState(false);
  const { t, fade } = useReelClock(paused);
  const frame = useMemo(() => frameAt(t), [t]);
  const done = frame.stage !== "trim";

  return (
    <figure className="relative">
      <Brackets className="border-primary/70" />
      <div className="relative overflow-hidden rounded-md bg-card shadow-2xl shadow-black/50 ring-1 ring-border">
        <figcaption className="flex items-center justify-between gap-3 border-b px-4 py-2.5 font-mono text-2xs tracking-wider text-muted-foreground uppercase">
          <span className="sr-only">
            Illustration: a playhead razors the intro and outro off five clips, the lane closes up
            into one shorter compilation, and the result renders to an MP4.
          </span>
          <span className="relative grid" aria-hidden="true">
            <span
              className={cn(
                "col-start-1 row-start-1 text-cut transition-opacity duration-300",
                done && "opacity-0",
              )}
            >
              Raw uploads
            </span>
            <span
              className={cn(
                "col-start-1 row-start-1 text-keep transition-opacity duration-300",
                !done && "opacity-0",
              )}
            >
              compilation.mp4
            </span>
          </span>
          <span className="flex shrink-0 items-center gap-3 tabular-nums">
            <span className="flex items-center gap-3" aria-hidden="true">
              <span className="hidden sm:inline">Runtime</span>
              <span className="text-sm text-primary">{formatTimecode(frame.runtime)}</span>
              <span className="hidden w-[4.5rem] text-cut sm:inline">
                {frame.cutAway > 0 ? `−${formatTimecode(frame.cutAway)}` : ""}
              </span>
            </span>
            <button
              type="button"
              onClick={() => setPaused((was) => !was)}
              aria-label={paused ? "Play animation" : "Pause animation"}
              className="focus-ring -my-1 -mr-1.5 grid size-6 place-items-center rounded-sm text-muted-foreground hover:text-foreground motion-reduce:hidden"
            >
              {paused ? <PlayIcon className="size-3.5" /> : <PauseIcon className="size-3.5" />}
            </button>
          </span>
        </figcaption>

        <div
          aria-hidden="true"
          className="grid grid-cols-[1.75rem_minmax(0,1fr)] grid-rows-[1.25rem_3.5rem_2.25rem_1.25rem_auto] gap-x-2 gap-y-2 p-3 sm:grid-cols-[2rem_minmax(0,1fr)] sm:p-4"
          style={{ opacity: fade }}
        >
          <div
            className="tl-ruler relative col-start-2 row-start-1"
            style={{ "--tick": "12.5%" } as React.CSSProperties}
          >
            {RULER_STOPS.map((stop, i) => (
              <span
                key={stop}
                className={cn(
                  "absolute top-0 pl-1 font-mono text-2xs leading-4 text-muted-foreground tabular-nums",
                  i % 2 === 1 && "hidden sm:block",
                )}
                style={{ left: `${stop * 100}%` }}
              >
                {formatTimecode(frame.runtime * stop)}
              </span>
            ))}
          </div>

          <span className="col-start-1 row-start-2 self-center font-mono text-2xs text-muted-foreground">V1</span>
          <Lane frame={frame} className="col-start-2 row-start-2" audio={false} />

          <span className="col-start-1 row-start-3 self-center font-mono text-2xs text-muted-foreground">A1</span>
          <Lane frame={frame} className="col-start-2 row-start-3" audio />

          <Playhead frame={frame} />

          <div className="col-start-2 row-start-5 flex items-center gap-3 font-mono text-2xs text-muted-foreground">
            <span className="w-[6.5rem] shrink-0 tabular-nums">{STATUS[frame.stage](frame)}</span>
            <span className="bg-hatch-raw h-1.5 flex-1 overflow-hidden rounded-full">
              <span className="block h-full bg-primary" style={{ width: `${frame.render * 100}%` }} />
            </span>
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-x-5 gap-y-1 border-t px-4 py-2.5 font-mono text-2xs text-muted-foreground">
          <Legend className="bg-keep">Kept</Legend>
          <Legend className="bg-hatch-cut">Cut away</Legend>
          <Legend className="bg-primary/60">Audio</Legend>
        </div>
      </div>
    </figure>
  );
}

const STATUS: Record<Frame["stage"], (frame: Frame) => string> = {
  trim: () => "Trimming",
  play: () => "Playing",
  render: (frame) => `Rendering ${Math.round(frame.render * 100)}%`,
  done: () => "Rendered 100%",
};

/**
 * One playhead across the ruler and both lanes. The rose razor is a separate mark over the lanes,
 * above the mint line, with its IN/OUT tag in its own row below so it never covers a ruler label.
 */
function Playhead({ frame }: { frame: Frame }) {
  const { head, razor } = frame;
  const flip = head > 0.86;
  return (
    <div className="pointer-events-none relative z-10 col-start-2 row-span-4 row-start-1">
      <div className="absolute inset-y-0 w-px -translate-x-1/2 bg-primary shadow-glow" style={{ left: `${head * 100}%` }}>
        <span className="absolute -top-0.5 -left-[5px] size-[11px] rotate-45 rounded-[2px] bg-primary" />
      </div>
      <div
        className="absolute top-7 bottom-5 w-0.5 -translate-x-1/2 bg-cut"
        style={{ left: `${head * 100}%`, opacity: razor.opacity }}
      />
      <span
        className={cn(
          "absolute bottom-0 rounded-[2px] bg-cut px-1 font-mono text-2xs leading-4 font-semibold text-background",
          flip ? "-translate-x-full" : "translate-x-0",
        )}
        style={{ left: `${head * 100}%`, opacity: razor.opacity }}
      >
        {razor.label}
      </span>
    </div>
  );
}

function Lane({ frame, className, audio }: { frame: Frame; className: string; audio: boolean }) {
  return (
    // The hatch is the lane's own background, so every cut block shares one phase and there is
    // no seam between neighbours. Kept footage is opaque and covers it.
    <div className={cn("bg-hatch-cut flex w-full overflow-hidden rounded-sm ring-1 ring-border/60", className)}>
      {SEGMENTS.map((segment, i) => {
        const style = { flexGrow: frame.grow[i] ?? 0, flexBasis: 0 };
        if (segment.kind !== "body") return <div key={i} className="min-w-0" style={style} />;
        const clip = CLIPS[segment.clip];
        if (!clip) return null;
        return audio ? (
          <div
            key={i}
            className="flex min-w-0 items-center justify-between overflow-hidden bg-[color-mix(in_oklch,var(--primary)_15%,var(--card))] px-1 shadow-[inset_1px_0_0_var(--card),inset_-1px_0_0_var(--card)]"
            style={style}
          >
            {WAVE.slice(segment.clip, segment.clip + Math.round(clip.body * 1.3)).map((height, n) => (
              <span
                key={n}
                className="w-[2px] shrink-0 rounded-full bg-primary/70"
                style={{ height: `${height * 9}%` }}
              />
            ))}
          </div>
        ) : (
          <div
            key={i}
            className="flex min-w-0 flex-col justify-between overflow-hidden bg-keep px-1.5 py-1 text-2xs font-semibold text-background shadow-[inset_1px_0_0_var(--card),inset_-1px_0_0_var(--card)]"
            style={style}
          >
            <span className="truncate">
              <span className="sm:hidden">{segment.clip + 1}</span>
              <span className="hidden sm:inline">{clip.label}</span>
            </span>
            <span className="h-1 w-6 rounded-full bg-background/30" />
          </div>
        );
      })}
    </div>
  );
}

function Legend({ className, children }: { className: string; children: React.ReactNode }) {
  return (
    <span className="inline-flex items-center gap-1.5">
      <span className={cn("h-2 w-4 rounded-[2px]", className)} />
      {children}
    </span>
  );
}
