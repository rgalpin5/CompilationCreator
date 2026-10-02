"use client";

import { useRef } from "react";
import { cn } from "@/lib/utils";
import { formatTimecode, PAGE_SECONDS, SECTION_TIMES, TC } from "./timeline";
import { useTimeline } from "./useTimeline";

const MARKERS = [
  { href: "#top", label: "Intro", time: SECTION_TIMES.intro, flip: false },
  { href: "#how", label: "How", time: SECTION_TIMES.how, flip: false },
  { href: "#get-access", label: "Access", time: SECTION_TIMES.access, flip: true },
];

/** A ruler label sits on this major tick, two minutes in. */
const TICK_LABEL_TIME = 120;

/** A fixed transport bar. Scrolling the page scrubs its playhead and its timecode. */
export default function Transport() {
  const headRef = useRef<HTMLDivElement>(null);
  const tcRef = useRef<HTMLSpanElement>(null);
  const navRef = useRef<HTMLElement>(null);

  // The bar is scaled to the timeline's real end so the playhead moves at a constant speed and
  // still reaches the right edge. Ticks, flags and labels are all multiples of 30 seconds.
  useTimeline((time, end) => {
    const nav = navRef.current;
    if (nav) {
      nav.style.setProperty("--end", String(end));
      nav.querySelectorAll<HTMLElement>("[data-time]").forEach((element) => {
        element.style.left = `${(Number(element.dataset.time) / end) * 100}%`;
      });
      const ruler = nav.querySelector<HTMLElement>("[data-ruler]");
      ruler?.style.setProperty("--tick", `${(30 / end) * 100}%`);
      const last = nav.querySelector<HTMLElement>("[data-end]");
      if (last) last.textContent = formatTimecode(end);
    }
    if (headRef.current) headRef.current.style.left = `${(time / end) * 100}%`;
    if (tcRef.current) tcRef.current.textContent = formatTimecode(time);
  });

  return (
    <div data-transport className="fixed inset-x-0 bottom-0 z-20 h-12 border-t bg-background/90 backdrop-blur-md">
      <div className="mx-auto flex h-full w-full max-w-7xl items-stretch px-4 md:px-6">
        <div className="flex w-[5.25rem] shrink-0 items-center gap-2 font-mono text-xs text-primary tabular-nums md:w-24">
          <span aria-hidden="true" className="size-1.5 rounded-full bg-primary motion-reduce:hidden" />
          <span ref={tcRef} aria-hidden="true" className="motion-reduce:hidden">
            {TC.intro}
          </span>
        </div>
        <nav ref={navRef} aria-label="Jump to section" className="relative h-full min-w-0 flex-1">
          <div
            aria-hidden="true"
            data-ruler
            className="tl-ruler absolute inset-x-0 top-0 h-3"
            style={{ "--tick": `${(30 / PAGE_SECONDS) * 100}%` } as React.CSSProperties}
          />
          <span
            aria-hidden="true"
            data-time={TICK_LABEL_TIME}
            className="absolute top-0 ml-1 hidden font-mono text-2xs leading-3 text-muted-foreground tabular-nums sm:block"
            style={{ left: `${(TICK_LABEL_TIME / PAGE_SECONDS) * 100}%` }}
          >
            {formatTimecode(TICK_LABEL_TIME)}
          </span>
          <span
            aria-hidden="true"
            data-end
            className="absolute top-0 right-0 font-mono text-2xs leading-3 text-muted-foreground tabular-nums"
          >
            {formatTimecode(PAGE_SECONDS)}
          </span>
          <div aria-hidden="true" className="pointer-events-none absolute inset-0 motion-reduce:hidden">
            <div ref={headRef} className="absolute inset-y-0 left-0 z-10 w-px bg-primary shadow-glow">
              <span className="absolute -top-0.5 -left-[4px] size-[9px] rotate-45 rounded-[2px] bg-primary" />
            </div>
          </div>
          {MARKERS.map((marker) => (
            <a
              key={marker.href}
              href={marker.href}
              data-time={marker.time}
              style={{ left: `${(marker.time / PAGE_SECONDS) * 100}%` }}
              className={cn(
                "focus-ring absolute bottom-0.5 flex min-h-6 items-center gap-1.5 rounded-sm font-mono text-2xs tracking-widest text-muted-foreground uppercase hover:text-foreground",
                marker.flip && "-translate-x-full flex-row-reverse",
              )}
            >
              <span
                aria-hidden="true"
                className={cn(
                  "h-3 w-2 bg-primary/80 [clip-path:polygon(0_0,100%_0,100%_60%,50%_100%,0_60%)]",
                  marker.flip ? "translate-x-px" : "-translate-x-px",
                )}
              />
              {marker.label}
            </a>
          ))}
        </nav>
      </div>
    </div>
  );
}
