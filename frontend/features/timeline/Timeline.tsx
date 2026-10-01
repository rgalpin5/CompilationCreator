"use client";

import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import { formatSeconds, parseTime } from "@/lib/time";
import type { TimelineClip } from "./types";

type Props = {
  clips: TimelineClip[];
  disabled?: boolean;
  onRemove: (index: number) => void;
  onMove: (index: number, direction: -1 | 1) => void;
};

/** The ordered clip list, with remove and reorder controls. */
export default function Timeline({ clips, disabled, onRemove, onMove }: Props) {
  if (clips.length === 0) {
    return (
      <p className="rounded-lg border border-dashed px-3 py-6 text-center text-sm text-muted-foreground">
        Add videos. Export opens a step where you cut each intro and outro.
      </p>
    );
  }

  return (
    <ScrollArea className="max-h-[60vh]">
      <ol className="flex flex-col gap-3 pr-3">
        {clips.map((clip, i) => {
          const start = parseTime(clip.start);
          const end = parseTime(clip.end);
          const introCut = start ?? 0;
          const outroCut =
            clip.duration_seconds != null && end != null
              ? Math.max(0, Math.floor(clip.duration_seconds) - end)
              : null;
          const hasCut = introCut > 0 || (outroCut != null && outroCut > 0);
          return (
            <li key={clip.video_id} className="flex flex-col gap-2 rounded-lg bg-muted/50 p-2">
              <div className="flex items-start justify-between gap-2">
                <span className="text-sm font-medium">
                  <span className="mr-1.5 inline-flex size-5 items-center justify-center rounded-full bg-primary text-xs text-primary-foreground">
                    {i + 1}
                  </span>
                  {clip.title}
                </span>
                <div className="flex shrink-0 gap-1">
                  <Button
                    type="button"
                    size="icon-sm"
                    variant="outline"
                    aria-label={`Move ${clip.title} up`}
                    disabled={disabled || i === 0}
                    onClick={() => onMove(i, -1)}
                  >
                    ↑
                  </Button>
                  <Button
                    type="button"
                    size="icon-sm"
                    variant="outline"
                    aria-label={`Move ${clip.title} down`}
                    disabled={disabled || i === clips.length - 1}
                    onClick={() => onMove(i, 1)}
                  >
                    ↓
                  </Button>
                  <Button
                    type="button"
                    size="sm"
                    variant="destructive"
                    aria-label={`Remove ${clip.title}`}
                    disabled={disabled}
                    onClick={() => onRemove(i)}
                  >
                    Remove
                  </Button>
                </div>
              </div>
              {hasCut && start != null && end != null && (
                <p className="text-xs text-muted-foreground tabular-nums">
                  {introCut > 0 ? `${formatSeconds(introCut)} intro cut` : "No intro cut"}
                  {" · "}
                  {outroCut != null && outroCut > 0
                    ? `${formatSeconds(outroCut)} outro cut`
                    : "No outro cut"}
                </p>
              )}
            </li>
          );
        })}
      </ol>
    </ScrollArea>
  );
}
