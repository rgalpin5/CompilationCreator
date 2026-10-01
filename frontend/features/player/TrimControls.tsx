"use client";

import { Button } from "@/components/ui/button";
import { defaultEnd } from "@/lib/time";

const SKIP_SECONDS = [
  { seconds: 10, label: "10s" },
  { seconds: 30, label: "30s" },
  { seconds: 60, label: "1 min" },
] as const;

type Props = {
  disabled?: boolean;
  canMark: boolean;
  duration: number | null;
  startSec: number;
  endSec: number;
  onSeek: (seconds: number) => void;
  onCommit: (which: "start" | "end", point: number) => void;
  onCutHere: (which: "start" | "end") => void;
  onUseFull: (end: string) => void;
};

/** Intro and outro buttons, including the action that keeps the full video. */
export default function TrimControls({
  disabled,
  canMark,
  duration,
  startSec,
  endSec,
  onSeek,
  onCommit,
  onCutHere,
  onUseFull,
}: Props) {
  return (
    <>
      <div className="grid gap-2 sm:grid-cols-2">
        <div className="flex flex-col gap-2 rounded-lg bg-muted/50 p-2">
          <p className="text-xs font-medium">Intro</p>
          <div className="flex flex-wrap gap-1.5">
            <Button type="button" size="sm" variant="outline" disabled={!canMark} onClick={() => onSeek(0)}>
              Play
            </Button>
            <Button type="button" size="sm" disabled={!canMark} onClick={() => onCutHere("start")}>
              Cut here
            </Button>
            {SKIP_SECONDS.map((skip) => (
              <Button
                key={skip.label}
                type="button"
                size="sm"
                variant="secondary"
                disabled={disabled}
                onClick={() => onCommit("start", startSec + skip.seconds)}
              >
                Skip {skip.label}
              </Button>
            ))}
          </div>
        </div>
        <div className="flex flex-col gap-2 rounded-lg bg-muted/50 p-2">
          <p className="text-xs font-medium">Outro</p>
          <div className="flex flex-wrap gap-1.5">
            <Button
              type="button"
              size="sm"
              variant="outline"
              disabled={!canMark}
              onClick={() => onSeek(Math.max(0, (duration ?? endSec) - 25))}
            >
              Play
            </Button>
            <Button type="button" size="sm" disabled={!canMark} onClick={() => onCutHere("end")}>
              Cut here
            </Button>
            {SKIP_SECONDS.map((skip) => (
              <Button
                key={skip.label}
                type="button"
                size="sm"
                variant="secondary"
                disabled={disabled}
                onClick={() => onCommit("end", endSec - skip.seconds)}
              >
                Trim {skip.label}
              </Button>
            ))}
          </div>
        </div>
      </div>

      <div className="flex justify-end">
        <Button
          type="button"
          size="sm"
          variant="ghost"
          disabled={disabled || duration == null}
          onClick={() => onUseFull(defaultEnd(duration))}
        >
          Use full video
        </Button>
      </div>
    </>
  );
}
