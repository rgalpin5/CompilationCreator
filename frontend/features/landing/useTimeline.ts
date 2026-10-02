"use client";

import { useEffect, useRef } from "react";
import { readAnchors, timelineAt } from "./timeline";

/** Calls back with the page time and the timeline end on mount, on every scroll frame and on resize. */
export function useTimeline(onTime: (time: number, end: number) => void): void {
  const latest = useRef(onTime);
  useEffect(() => {
    latest.current = onTime;
  });

  useEffect(() => {
    let frame = 0;
    function update() {
      frame = 0;
      const { time, end } = timelineAt(window.scrollY, readAnchors());
      latest.current(time, end);
    }
    function schedule() {
      if (!frame) frame = requestAnimationFrame(update);
    }
    schedule();
    window.addEventListener("scroll", schedule, { passive: true });
    window.addEventListener("resize", schedule);
    return () => {
      window.removeEventListener("scroll", schedule);
      window.removeEventListener("resize", schedule);
      if (frame) cancelAnimationFrame(frame);
    };
  }, []);
}
