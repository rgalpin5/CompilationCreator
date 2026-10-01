"use client";

import { ArrowDownIcon, ArrowUpIcon, CloseIcon } from "@/components/icons";
import TrimStrip from "@/components/TrimStrip";
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
      <p className="rounded-lg border border-dashed px-3 py-8 text-center text-sm text-muted-foreground">
        Click videos to add them here.
      </p>
    );
  }

  return (
    <ScrollArea className="max-h-[60vh]">
      <ol className="flex flex-col gap-2 pr-3">
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
            <li key={clip.video_id} className="group flex flex-col gap-2 rounded-lg bg-muted/60 p-2.5">
              <div className="flex items-start justify-between gap-2">
                <span className="flex min-w-0 gap-2 text-sm leading-snug">
                  <span className="mt-px flex h-5 min-w-5 shrink-0 items-center justify-center rounded bg-primary px-1 font-mono text-[11px] font-semibold text-primary-foreground tabular-nums">
                    {i + 1}
                  </span>
                  <span className="line-clamp-2">{clip.title}</span>
                </span>
                <div className="flex shrink-0 gap-0.5">
                  <Button
                    type="button"
                    size="icon-sm"
                    variant="ghost"
                    aria-label="Move up"
                    disabled={disabled || i === 0}
                    onClick={() => onMove(i, -1)}
                  >
                    <ArrowUpIcon />
                  </Button>
                  <Button
                    type="button"
                    size="icon-sm"
                    variant="ghost"
                    aria-label="Move down"
                    disabled={disabled || i === clips.length - 1}
                    onClick={() => onMove(i, 1)}
                  >
                    <ArrowDownIcon />
                  </Button>
                  <Button
                    type="button"
                    size="icon-sm"
                    variant="ghost"
                    aria-label="Remove"
                    className="hover:bg-destructive/15 hover:text-destructive"
                    disabled={disabled}
                    onClick={() => onRemove(i)}
                  >
                    <CloseIcon />
                  </Button>
                </div>
              </div>
              {clip.duration_seconds != null && (
                <TrimStrip
                  duration={clip.duration_seconds}
                  start={start ?? 0}
                  end={end ?? clip.duration_seconds}
                />
              )}
              {hasCut && start != null && end != null && (
                <p className="font-mono text-[11px] text-muted-foreground tabular-nums">
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
