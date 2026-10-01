"use client";

import { useRef, type KeyboardEvent, type PointerEvent as ReactPointerEvent } from "react";
import { formatSeconds } from "@/lib/time";

type Props = {
  duration: number;
  start: number;
  end: number;
  playhead: number;
  disabled?: boolean;
  onSeek: (seconds: number) => void;
  onChangeStart: (seconds: number) => void;
  onChangeEnd: (seconds: number) => void;
};

/** Drag handles and keyboard nudge for the kept range of one video. */
export default function TrimBar({
  duration,
  start,
  end,
  playhead,
  disabled,
  onSeek,
  onChangeStart,
  onChangeEnd,
}: Props) {
  const trackRef = useRef<HTMLDivElement>(null);

  function secondsFromClientX(clientX: number) {
    const rect = trackRef.current?.getBoundingClientRect();
    if (!rect || rect.width <= 0) return 0;
    const ratio = Math.min(1, Math.max(0, (clientX - rect.left) / rect.width));
    return ratio * duration;
  }

  function beginDrag(event: ReactPointerEvent<HTMLElement>, apply: (seconds: number) => void) {
    if (disabled) return;
    event.preventDefault();
    event.stopPropagation();
    const target = event.currentTarget;
    target.setPointerCapture(event.pointerId);
    apply(secondsFromClientX(event.clientX));
    const onMove = (ev: PointerEvent) => apply(secondsFromClientX(ev.clientX));
    const onUp = (ev: PointerEvent) => {
      if (target.hasPointerCapture(ev.pointerId)) {
        target.releasePointerCapture(ev.pointerId);
      }
      target.removeEventListener("pointermove", onMove);
      target.removeEventListener("pointerup", onUp);
    };
    target.addEventListener("pointermove", onMove);
    target.addEventListener("pointerup", onUp);
  }

  function nudge(which: "start" | "end", key: string, shift: boolean) {
    const step = shift ? 5 : 1;
    const delta = key === "ArrowLeft" ? -step : key === "ArrowRight" ? step : 0;
    if (delta === 0) return false;
    if (which === "start") onChangeStart(start + delta);
    else onChangeEnd(end + delta);
    return true;
  }

  const startPct = (start / duration) * 100;
  const endPct = (end / duration) * 100;
  const playPct = (playhead / duration) * 100;

  return (
    <div className="flex flex-col gap-1">
      <div className="relative h-8">
        <div
          ref={trackRef}
          className="absolute inset-x-0 top-2.5 h-3 cursor-pointer overflow-hidden rounded-full bg-hatch-cut touch-none"
          onPointerDown={(event) => beginDrag(event, onSeek)}
        >
          <div
            className="absolute inset-y-0 bg-keep"
            style={{ left: `${startPct}%`, width: `${Math.max(0, endPct - startPct)}%` }}
          />
        </div>
        <div
          className="pointer-events-none absolute top-0.5 h-7 w-0.5 -translate-x-1/2 rounded-full bg-primary shadow-glow"
          style={{ left: `${playPct}%` }}
        />
        <Handle
          label="Intro cut"
          now={start}
          max={duration}
          percent={startPct}
          disabled={disabled}
          onPointerDown={(event) => beginDrag(event, onChangeStart)}
          onKeyDown={(event) => {
            if (nudge("start", event.key, event.shiftKey)) event.preventDefault();
          }}
        />
        <Handle
          label="Outro cut"
          now={end}
          max={duration}
          percent={endPct}
          disabled={disabled}
          onPointerDown={(event) => beginDrag(event, onChangeEnd)}
          onKeyDown={(event) => {
            if (nudge("end", event.key, event.shiftKey)) event.preventDefault();
          }}
        />
      </div>
      <div className="flex justify-between font-mono text-2xs text-muted-foreground tabular-nums">
        <span>Start {formatSeconds(start)}</span>
        <span className="text-keep">{formatSeconds(end - start)} kept</span>
        <span>End {formatSeconds(end)}</span>
      </div>
    </div>
  );
}

function Handle({
  label,
  now,
  max,
  percent,
  disabled,
  onPointerDown,
  onKeyDown,
}: {
  label: string;
  now: number;
  max: number;
  percent: number;
  disabled?: boolean;
  onPointerDown: (event: ReactPointerEvent<HTMLButtonElement>) => void;
  onKeyDown: (event: KeyboardEvent<HTMLButtonElement>) => void;
}) {
  return (
    <button
      type="button"
      role="slider"
      aria-label={label}
      aria-valuemin={0}
      aria-valuemax={Math.floor(max)}
      aria-valuenow={Math.round(now)}
      aria-valuetext={formatSeconds(now)}
      disabled={disabled}
      onPointerDown={onPointerDown}
      onKeyDown={onKeyDown}
      className="absolute top-1 h-6 w-2.5 -translate-x-1/2 cursor-ew-resize rounded-sm border-2 border-foreground bg-background shadow-md touch-none focus-visible:ring-3 focus-visible:ring-ring/60 focus-visible:outline-none disabled:opacity-50"
      style={{ left: `${percent}%` }}
    />
  );
}
