"use client";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ScrollArea } from "@/components/ui/scroll-area";

export type TimelineClip = {
  video_id: string;
  title: string;
  start: string;
  end: string;
  channel?: string | null;
  view_count?: number | null;
  duration_seconds?: number | null;
  thumbnail?: string | null;
};

type Props = {
  clips: TimelineClip[];
  disabled?: boolean;
  onChange: (index: number, patch: Partial<TimelineClip>) => void;
  onRemove: (index: number) => void;
  onMove: (index: number, direction: -1 | 1) => void;
};

export default function Timeline({
  clips,
  disabled,
  onChange,
  onRemove,
  onMove,
}: Props) {
  if (clips.length === 0) {
    return (
      <p className="rounded-lg border border-dashed px-3 py-6 text-center text-sm text-muted-foreground">
        Add 4–8 videos. Each one is trimmed from the start through the end time,
        and the whole video is filled in when its length is known.
      </p>
    );
  }

  return (
    <ScrollArea className="max-h-[60vh]">
      <ol className="flex flex-col gap-3 pr-3">
        {clips.map((clip, i) => (
          <li
            key={clip.video_id}
            className="flex flex-col gap-2 rounded-lg bg-muted/50 p-2"
          >
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
                  aria-label="Move up"
                  disabled={disabled || i === 0}
                  onClick={() => onMove(i, -1)}
                >
                  ↑
                </Button>
                <Button
                  type="button"
                  size="icon-sm"
                  variant="outline"
                  aria-label="Move down"
                  disabled={disabled || i === clips.length - 1}
                  onClick={() => onMove(i, 1)}
                >
                  ↓
                </Button>
                <Button
                  type="button"
                  size="sm"
                  variant="destructive"
                  disabled={disabled}
                  onClick={() => onRemove(i)}
                >
                  Remove
                </Button>
              </div>
            </div>
            <div className="flex gap-2">
              <label className="flex flex-1 flex-col gap-1 text-xs text-muted-foreground">
                Start
                <Input
                  value={clip.start}
                  placeholder="00:00"
                  disabled={disabled}
                  onChange={(e) => onChange(i, { start: e.target.value })}
                />
              </label>
              <label className="flex flex-1 flex-col gap-1 text-xs text-muted-foreground">
                End
                <Input
                  value={clip.end}
                  placeholder="30:00"
                  disabled={disabled}
                  onChange={(e) => onChange(i, { end: e.target.value })}
                />
              </label>
            </div>
          </li>
        ))}
      </ol>
    </ScrollArea>
  );
}
