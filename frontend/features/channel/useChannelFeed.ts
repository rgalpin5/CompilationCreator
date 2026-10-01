"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { fetchChannelVideos } from "@/lib/api/channels";
import { fetchUsage } from "@/lib/api/usage";
import type { Video } from "@/lib/api/types";
import { errorMessage } from "@/lib/errors";

const PAGE_SIZE = 24;

export type ChannelFeed = {
  videos: Video[];
  loadingVideos: boolean;
  loadingMore: boolean;
  hasMore: boolean;
  loadError: string | null;
  moreError: string | null;
  loadVideos: (url: string) => Promise<void>;
  loadMore: () => Promise<void>;
  refreshUsage: (isCurrent: () => boolean) => Promise<void>;
};

/** Channel pages, load errors, and the usage-count refresh after an export. */
export function useChannelFeed(): ChannelFeed {
  const [videos, setVideos] = useState<Video[]>([]);
  const [loadingVideos, setLoadingVideos] = useState(false);
  const [loadingMore, setLoadingMore] = useState(false);
  const [hasMore, setHasMore] = useState(false);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [moreError, setMoreError] = useState<string | null>(null);
  const feedRef = useRef({
    generation: 0,
    url: null as string | null,
    nextOffset: 0,
    hasMore: false,
    loadingMore: false,
  });
  const videoIdsRef = useRef<string[]>([]);

  useEffect(() => {
    videoIdsRef.current = videos.map((video) => video.video_id);
  }, [videos]);

  async function loadVideos(url: string): Promise<void> {
    const feed = feedRef.current;
    feed.generation += 1;
    const generation = feed.generation;
    feed.url = url;
    feed.nextOffset = 0;
    feed.hasMore = false;
    feed.loadingMore = false;
    setHasMore(false);
    setMoreError(null);
    setLoadError(null);
    setLoadingVideos(true);
    setVideos([]);
    try {
      const page = await fetchChannelVideos(url, PAGE_SIZE, 0);
      if (feedRef.current.generation !== generation) return;
      setVideos(page.videos);
      feed.nextOffset = page.next_offset;
      feed.hasMore = page.has_more;
      setHasMore(page.has_more);
    } catch (caught: unknown) {
      if (feedRef.current.generation !== generation) return;
      setLoadError(errorMessage(caught));
    } finally {
      if (feedRef.current.generation === generation) setLoadingVideos(false);
    }
  }

  const loadMore = useCallback(async () => {
    const feed = feedRef.current;
    if (!feed.url || !feed.hasMore || feed.loadingMore) return;
    const generation = feed.generation;
    const url = feed.url;
    const offset = feed.nextOffset;
    feed.loadingMore = true;
    setLoadingMore(true);
    setMoreError(null);
    try {
      const page = await fetchChannelVideos(url, PAGE_SIZE, offset);
      if (feedRef.current.generation !== generation) return;
      setVideos((prev) => {
        const seen = new Set(prev.map((video) => video.video_id));
        const extra = page.videos.filter((video) => !seen.has(video.video_id));
        return extra.length > 0 ? [...prev, ...extra] : prev;
      });
      feed.nextOffset = page.next_offset;
      const more = page.has_more && page.videos.length > 0;
      feed.hasMore = more;
      setHasMore(more);
    } catch (caught: unknown) {
      if (feedRef.current.generation !== generation) return;
      setMoreError(errorMessage(caught));
    } finally {
      if (feedRef.current.generation === generation) {
        feed.loadingMore = false;
        setLoadingMore(false);
      }
    }
  }, []);

  const refreshUsage = useCallback(async (isCurrent: () => boolean) => {
    try {
      const counts = await fetchUsage(videoIdsRef.current);
      if (!isCurrent()) return;
      setVideos((prev) =>
        prev.map((video) => ({
          ...video,
          compilation_count: counts[video.video_id] ?? video.compilation_count,
        })),
      );
    } catch (caught: unknown) {
      // The export already finished. Only a failed usage request is ignored.
      if (caught instanceof Error) return;
      throw caught;
    }
  }, []);

  return {
    videos,
    loadingVideos,
    loadingMore,
    hasMore,
    loadError,
    moreError,
    loadVideos,
    loadMore,
    refreshUsage,
  };
}
