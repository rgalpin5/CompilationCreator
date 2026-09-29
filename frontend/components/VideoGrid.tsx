"use client";

import type { Video } from "@/lib/api";
import { formatSeconds } from "@/lib/time";
import { Card, CardContent } from "@/components/ui/card";
import { cn } from "@/lib/utils";

type Props = {
  videos: Video[];
  selectedIds: Set<string>;
  onSelect: (video: Video) => void;
};

export default function VideoGrid({ videos, selectedIds, onSelect }: Props) {
  if (videos.length === 0) {
    return (
      <div className="flex min-h-48 items-center justify-center rounded-xl border border-dashed bg-card px-6 text-center text-sm text-muted-foreground">
        No videos loaded yet. Enter a channel URL above.
      </div>
    );
  }

  return (
    <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4">
      {videos.map((video) => {
        const selected = selectedIds.has(video.video_id);
        return (
          <button
            key={video.video_id}
            type="button"
            onClick={() => onSelect(video)}
            aria-pressed={selected}
            className="rounded-xl text-left"
          >
            <Card
              size="sm"
              className={cn(
                "h-full pt-0 shadow-sm transition hover:-translate-y-0.5",
                selected
                  ? "ring-2 ring-primary"
                  : "ring-foreground/10 hover:ring-foreground/25",
              )}
            >
              <div className="relative aspect-video w-full bg-muted">
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img
                  src={video.thumbnail}
                  alt=""
                  className="h-full w-full object-cover"
                  loading="lazy"
                />
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
      })}
    </div>
  );
}
