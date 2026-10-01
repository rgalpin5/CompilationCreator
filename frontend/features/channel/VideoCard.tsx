"use client";

import type { Video } from "@/lib/api/types";
import { formatSeconds } from "@/lib/time";
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
          "h-full pt-0 shadow-sm transition hover:-translate-y-0.5",
          selected ? "ring-2 ring-primary" : "ring-foreground/10 hover:ring-foreground/25",
        )}
      >
        <div className="relative aspect-video w-full bg-muted">
          <LazyThumbnail src={video.thumbnail} />
          {selected && (
            <span className="absolute top-1 left-1 rounded bg-primary px-1.5 py-0.5 text-xs text-primary-foreground">
              Added
            </span>
          )}
          {video.duration_seconds != null && (
            <span className="absolute right-1 bottom-1 rounded bg-black/70 px-1 text-xs text-white">
              {formatSeconds(video.duration_seconds)}
            </span>
          )}
        </div>
        <CardContent>
          <p className="line-clamp-2 text-sm">{video.title}</p>
          <p className="mt-2 inline-flex rounded-full bg-muted px-2 py-0.5 text-xs text-muted-foreground">
            {(video.compilation_count ?? 0) === 1
              ? "Used in 1 compilation"
              : `Used in ${video.compilation_count ?? 0} compilations`}
          </p>
        </CardContent>
      </Card>
    </button>
  );
}
