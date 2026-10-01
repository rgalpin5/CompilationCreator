"use client";

import { useEffect, useRef } from "react";
import type { Video } from "@/lib/api/types";
import { Button } from "@/components/ui/button";
import VideoCard from "./VideoCard";

type Props = {
  videos: Video[];
  selectedIds: Set<string>;
  onSelect: (video: Video) => void;
  loading: boolean;
  hasMore: boolean;
  loadingMore: boolean;
  moreError: string | null;
  onLoadMore: () => void;
};

/** The channel grid. Loads the next page when the last row comes into view. */
export default function VideoGrid({
  videos,
  selectedIds,
  onSelect,
  loading,
  hasMore,
  loadingMore,
  moreError,
  onLoadMore,
}: Props) {
  const sentinelRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const node = sentinelRef.current;
    if (!node || !hasMore || loadingMore || moreError) return;
    const observer = new IntersectionObserver(
      (entries) => {
        if (entries.some((entry) => entry.isIntersecting)) onLoadMore();
      },
      { rootMargin: "480px 0px" },
    );
    observer.observe(node);
    return () => observer.disconnect();
  }, [hasMore, loadingMore, moreError, onLoadMore]);

  if (videos.length === 0) {
    if (loading) return null;
    return (
      <div className="bg-frame-grid flex min-h-56 items-center justify-center rounded-xl border border-dashed px-6 text-center text-sm text-muted-foreground">
        Paste a channel link above to load its videos.
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-3">
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4">
        {videos.map((video) => (
          <VideoCard
            key={video.video_id}
            video={video}
            selected={selectedIds.has(video.video_id)}
            onSelect={onSelect}
          />
        ))}
      </div>
      {hasMore && (
        <div ref={sentinelRef} className="flex min-h-8 items-center justify-center">
          {moreError ? (
            <div className="flex flex-col items-center gap-2">
              <p className="text-sm text-destructive">{moreError}</p>
              <Button type="button" variant="outline" onClick={onLoadMore}>
                Try again
              </Button>
            </div>
          ) : (
            <p className="text-sm text-muted-foreground" aria-live="polite">
              {loadingMore ? "Loading more videos…" : ""}
            </p>
          )}
        </div>
      )}
    </div>
  );
}
