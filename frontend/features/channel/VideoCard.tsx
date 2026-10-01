"use client";

import type { Video } from "@/lib/api/types";
import { formatSeconds } from "@/lib/time";
import { CheckIcon } from "@/components/icons";
import { Card, CardContent } from "@/components/ui/card";
import { cn } from "@/lib/utils";
import LazyThumbnail from "./LazyThumbnail";

type Props = {
  video: Video;
  selected: boolean;
  onSelect: (video: Video) => void;
};

/** One channel video, selected when it is already on the timeline. */
export default function VideoCard({ video, selected, onSelect }: Props) {
  return (
    <button
      type="button"
      onClick={() => onSelect(video)}
      aria-pressed={selected}
      className="rounded-xl text-left"
    >
      <Card
        size="sm"
        className={cn(
          "h-full pt-0 transition duration-150 hover:-translate-y-0.5",
          selected ? "ring-2 ring-primary" : "ring-border hover:ring-foreground/25",
        )}
      >
        <div className="relative aspect-video w-full bg-muted">
          <LazyThumbnail src={video.thumbnail} />
          {selected && (
            <span className="absolute top-1.5 left-1.5 inline-flex items-center gap-1 rounded bg-primary px-1.5 py-0.5 text-xs font-medium text-primary-foreground">
              <CheckIcon className="size-3" strokeWidth={3} />
              Added
            </span>
          )}
          {video.duration_seconds != null && (
            <span className="absolute right-1.5 bottom-1.5 rounded bg-black/75 px-1 font-mono text-2xs text-white tabular-nums">
              {formatSeconds(video.duration_seconds)}
            </span>
          )}
        </div>
        <CardContent>
          <p className="line-clamp-2 text-sm leading-snug">{video.title}</p>
          <p
            className={cn(
              "mt-2 inline-flex rounded px-1.5 py-0.5 text-xs",
              (video.compilation_count ?? 0) > 0
                ? "bg-keep/15 text-keep"
                : "bg-muted text-muted-foreground",
            )}
          >
            {(video.compilation_count ?? 0) === 1
              ? "Used in 1 compilation"
              : `Used in ${video.compilation_count ?? 0} compilations`}
          </p>
        </CardContent>
      </Card>
    </button>
  );
}
