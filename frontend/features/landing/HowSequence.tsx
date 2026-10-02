"use client";

import { useRef, useState, type CSSProperties, type ReactNode } from "react";
import { cn } from "@/lib/utils";
import { ExportArt, PickArt, TrimArt } from "./StepArt";
import { formatTimecode, SEQUENCE_TIMES } from "./timeline";
import { useTimeline } from "./useTimeline";

const SPAN = SEQUENCE_TIMES.end - SEQUENCE_TIMES.start;

const STEPS = [
  {
    n: "01",
    title: "Pick",
    track: "V3",
    art: <PickArt />,
    body: "Paste a channel link. Its uploads load as a grid, newest first, with how often you have used each one.",
  },
  {
    n: "02",
    title: "Trim",
    track: "V2",
    art: <TrimArt />,
    body: "Step through every clip in a built-in player. Drag the handles or press Cut here to drop the intro and outro.",
  },
  {
    n: "03",
    title: "Export",
    track: "V1",
    art: <ExportArt />,
    body: "One MP4 in 1080p or 4K. Matching clips are joined without re-encoding, so long compilations finish fast.",
  },
].map((step, i, all) => {
  const start = i / all.length;
  const end = (i + 1) / all.length;
  return {
    ...step,
    start,
    end,
    in: formatTimecode(SEQUENCE_TIMES.start + start * SPAN),
    out: formatTimecode(SEQUENCE_TIMES.start + end * SPAN),
  };
});

type Step = (typeof STEPS)[number];

const LIMITS = [
  { label: "Clips per timeline", value: "100" },
  { label: "Output length", value: "4 h" },
  { label: "Resolution", value: "1080p or 4K" },
  { label: "Container", value: "MP4" },
];

const clamp01 = (x: number) => Math.min(1, Math.max(0, x));

/**
 * Three steps as a real multitrack. On large screens the section pins and one playhead crosses
 * V3, V2 and V1 as you scroll; each clip turns from unprocessed hatch to kept footage under it,
 * and the monitor above shows the step being crossed. The ruler and the playhead use the page
 * transport's own time, so the timecodes always agree. Elsewhere the steps stack as clips.
 * The pinned version is visual only; screen readers get the stacked list at every size.
 */
export default function HowSequence() {
  return (
    <div id="sequence">
      <PinnedSequence />
      <StackedSequence />
    </div>
  );
}

function PinnedSequence() {
  const stageRef = useRef<HTMLDivElement>(null);
  const headRef = useRef<HTMLDivElement>(null);
  const chipRef = useRef<HTMLSpanElement>(null);
  const [active, setActive] = useState(0);

  useTimeline((time) => {
    const p = clamp01((time - SEQUENCE_TIMES.start) / SPAN);
    const stage = stageRef.current;
    if (stage) {
      STEPS.forEach((step, i) => {
        stage.style.setProperty(`--lit-${i}`, String(clamp01((p - step.start) / (step.end - step.start))));
      });
    }
    if (headRef.current) headRef.current.style.left = `${p * 100}%`;
    if (chipRef.current) chipRef.current.textContent = formatTimecode(time);
    setActive(Math.min(STEPS.length - 1, Math.floor(p * STEPS.length)));
  });

  return (
    <div data-pin aria-hidden="true" className="hidden h-[calc(100svh-7rem+1500px)] lg:block motion-reduce:lg:hidden">
      <div
        ref={stageRef}
        className="sticky top-14 flex h-[calc(100svh-7rem)] min-h-[36rem] flex-col justify-between gap-6 py-4"
      >
        <div className="grid min-h-0 flex-1 items-center gap-12 lg:grid-cols-[minmax(0,5fr)_minmax(0,7fr)]">
          <div className="grid">
            {STEPS.map((step, i) => (
              <Pane key={step.title} on={active === i}>
                <div className="flex flex-col gap-5">
                  <span className="font-mono text-xs text-primary tabular-nums">
                    STEP {step.n} / 03 · IN {step.in}
                  </span>
                  <h3 className="font-heading text-7xl leading-[0.9] font-extrabold tracking-tight text-keep">
                    {step.title}
                  </h3>
                  <Copy>{step.body}</Copy>
                </div>
              </Pane>
            ))}
          </div>
          <div className="mx-auto grid w-full max-w-xl">
            {STEPS.map((step, i) => (
              <Pane key={step.title} on={active === i}>
                {step.art}
              </Pane>
            ))}
          </div>
        </div>

        <Timeline headRef={headRef} chipRef={chipRef} active={active} />
      </div>
    </div>
  );
}

function Pane({ on, children }: { on: boolean; children: ReactNode }) {
  return (
    <div
      className={cn(
        "col-start-1 row-start-1 transition-[opacity,translate] duration-500 ease-out",
        on ? "translate-y-0 opacity-100" : "pointer-events-none translate-y-3 opacity-0",
      )}
    >
      {children}
    </div>
  );
}

function Timeline({
  headRef,
  chipRef,
  active,
}: {
  headRef: React.RefObject<HTMLDivElement | null>;
  chipRef: React.RefObject<HTMLSpanElement | null>;
  active: number;
}) {
  const stops = Array.from({ length: 7 }, (_, i) => i / 6);
  return (
    <div className="relative rounded-md bg-card/60 p-3 ring-1 ring-border">
      <div className="grid grid-cols-[2.5rem_minmax(0,1fr)] gap-x-2 gap-y-1.5">
        <span />
        <div aria-hidden="true" className="tl-ruler relative h-6" style={{ "--tick": "16.6667%" } as CSSProperties}>
          {stops.map((stop, i) => (
            <span
              key={stop}
              className={cn(
                "absolute top-0 pl-1 font-mono text-2xs leading-4 text-muted-foreground tabular-nums",
                i === stops.length - 1 && "right-0 pl-0 pr-1",
              )}
              style={i === stops.length - 1 ? undefined : { left: `${stop * 100}%` }}
            >
              {formatTimecode(SEQUENCE_TIMES.start + stop * SPAN)}
            </span>
          ))}
        </div>
        {STEPS.map((step, i) => (
          <TrackRow key={step.title} step={step} index={i} current={active === i} />
        ))}
      </div>
      <div aria-hidden="true" className="pointer-events-none absolute inset-y-3 right-3 left-[3.75rem] z-10">
        <div ref={headRef} className="absolute inset-y-0 left-0 w-px bg-primary shadow-glow">
          <span className="absolute -top-0.5 -left-[5px] size-[11px] rotate-45 rounded-[2px] bg-primary" />
          <span
            ref={chipRef}
            className="absolute top-0 left-2 rounded-[2px] bg-primary px-1 font-mono text-2xs leading-4 font-semibold text-primary-foreground tabular-nums"
          >
            {formatTimecode(SEQUENCE_TIMES.start)}
          </span>
        </div>
      </div>
    </div>
  );
}

function TrackRow({ step, index, current }: { step: Step; index: number; current: boolean }) {
  return (
    <>
      <span
        className={cn(
          "self-center font-mono text-2xs transition-colors",
          current ? "text-primary" : "text-muted-foreground",
        )}
      >
        {step.track}
      </span>
      <div className="relative h-14 rounded-sm bg-muted/25 ring-1 ring-border/60">
        <div
          className="absolute inset-y-0 overflow-hidden rounded-sm"
          style={{ left: `${step.start * 100}%`, width: `${(step.end - step.start) * 100}%` }}
        >
          <ClipFace step={step} className="bg-hatch-raw text-muted-foreground" />
          <ClipFace
            step={step}
            className="bg-keep text-background shadow-[inset_-2px_0_0_var(--primary)]"
            style={{ clipPath: `inset(0 calc((1 - var(--lit-${index}, 0)) * 100%) 0 0)` }}
          />
        </div>
      </div>
    </>
  );
}

function ClipFace({ step, className, style }: { step: Step; className: string; style?: CSSProperties }) {
  return (
    <div className={cn("absolute inset-0 flex items-center justify-between gap-3 px-3", className)} style={style}>
      <span className="flex items-baseline gap-3">
        <span className="font-mono text-xs font-semibold tabular-nums">{step.n}</span>
        <span className="font-heading text-2xl leading-none font-extrabold tracking-tight">{step.title}</span>
      </span>
      <span className="font-mono text-2xs font-semibold tabular-nums">
        {step.in}
        <span aria-hidden="true"> → </span>
        {step.out}
      </span>
    </div>
  );
}

const COLUMNS = "md:grid-cols-3";

/**
 * Small screens, and reduced motion: the three clips stacked with the cut footage between them.
 * Where the pinned sequence shows instead, this stays in the accessibility tree as sr-only text.
 */
function StackedSequence() {
  return (
    <ol className={cn("grid gap-y-0 lg:sr-only motion-reduce:lg:not-sr-only motion-reduce:lg:grid", COLUMNS)}>
      {STEPS.map((step, i) => (
        <li key={step.title} className="contents">
          {i > 0 && <span aria-hidden="true" className="bg-hatch-cut my-3 h-5 rounded-sm md:hidden" />}
          <div className="flex min-w-0 flex-col gap-5 md:px-2.5">
            <div className="flex items-center justify-between rounded-sm bg-keep px-3 py-2 text-background">
              <span className="flex items-baseline gap-3">
                <span className="font-mono text-xs font-semibold tabular-nums">{step.n}</span>
                <h3 className="font-heading text-3xl leading-none font-extrabold tracking-tight md:text-4xl">
                  {step.title}
                </h3>
              </span>
              <span className="font-mono text-2xs leading-4 font-semibold tabular-nums">{step.in}</span>
            </div>
            {step.art}
            <Copy>{step.body}</Copy>
          </div>
        </li>
      ))}
    </ol>
  );
}

function Copy({ children }: { children: ReactNode }) {
  return <p className="max-w-prose text-sm leading-relaxed text-muted-foreground md:text-base lg:text-lg">{children}</p>;
}

/** The limits as an export dialog strip: the settings are the fields. */
export function Limits() {
  return (
    <div className="reveal-rise overflow-hidden rounded-md bg-card ring-1 ring-border">
      <div className="flex flex-wrap items-baseline justify-between gap-x-6 gap-y-1 border-b px-5 py-4">
        <h3 className="font-heading text-2xl leading-tight font-extrabold tracking-tight md:text-3xl">
          The limits, <span className="text-muted-foreground">up front.</span>
        </h3>
        <p className="font-mono text-2xs tracking-wider text-muted-foreground uppercase">
          export.settings · <span className="text-keep">MP4</span>
        </p>
      </div>
      <dl className="grid grid-cols-2 gap-px bg-border/60 lg:grid-cols-4">
        {LIMITS.map((limit) => (
          <div key={limit.label} className="flex flex-col gap-1.5 bg-card px-5 py-5">
            <dt className="font-mono text-2xs tracking-wider text-muted-foreground uppercase">{limit.label}</dt>
            <dd className="font-heading text-3xl font-bold tracking-tight text-primary tabular-nums md:text-4xl">
              {limit.value}
            </dd>
          </div>
        ))}
      </dl>
    </div>
  );
}
