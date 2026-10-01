"use client";

import { useState } from "react";
import { defaultEnd } from "@/lib/time";
import type { Video } from "@/lib/api/types";
import type { TimelineClip } from "./types";

function adjustAfterRemove(active: number, removed: number, length: number): number {
  const nextLength = length - 1;
  if (nextLength <= 0) return 0;
  if (active > removed) return active - 1;
  if (active === removed) return Math.min(removed, nextLength - 1);
  return active;
}

export type TimelineState = {
  clips: TimelineClip[];
  activeIndex: number;
  setActiveIndex: (index: number) => void;
  cutIndex: number;
  addVideo: (video: Video) => void;
  updateClip: (index: number, patch: Partial<TimelineClip>) => void;
  removeClip: (index: number) => void;
  moveClip: (index: number, direction: -1 | 1) => void;
};

/** The ordered clips and which one is selected. ``onEdit`` runs after each change. */
export function useTimeline(onEdit: () => void): TimelineState {
  const [clips, setClips] = useState<TimelineClip[]>([]);
  const [activeIndex, setActiveIndex] = useState(0);

  function addVideo(video: Video): void {
    onEdit();
    const existing = clips.findIndex((c) => c.video_id === video.video_id);
    if (existing >= 0) {
      setClips((prev) => prev.filter((c) => c.video_id !== video.video_id));
      setActiveIndex((current) => adjustAfterRemove(current, existing, clips.length));
      return;
    }
    setClips((prev) => [
      ...prev,
      {
        video_id: video.video_id,
        title: video.title,
        start: "00:00",
        end: defaultEnd(video.duration_seconds),
        channel: video.channel,
        view_count: video.view_count,
        duration_seconds: video.duration_seconds,
        thumbnail: video.thumbnail,
      },
    ]);
  }

  function updateClip(index: number, patch: Partial<TimelineClip>): void {
    onEdit();
    setClips((prev) => prev.map((c, i) => (i === index ? { ...c, ...patch } : c)));
  }

  function removeClip(index: number): void {
    onEdit();
    setClips((prev) => prev.filter((_, i) => i !== index));
    setActiveIndex((current) => adjustAfterRemove(current, index, clips.length));
  }

  function moveClip(index: number, direction: -1 | 1): void {
    const target = index + direction;
    if (target < 0 || target >= clips.length) return;
    onEdit();
    setClips((prev) => {
      const next = [...prev];
      const current = next[index];
      const destination = next[target];
      if (current === undefined || destination === undefined) return prev;
      next[index] = destination;
      next[target] = current;
      return next;
    });
    setActiveIndex((current) => {
      if (current === index) return target;
      if (current === target) return index;
      return current;
    });
  }

  const cutIndex = clips.length === 0 ? 0 : Math.min(activeIndex, clips.length - 1);

  return {
    clips,
    activeIndex,
    setActiveIndex,
    cutIndex,
    addVideo,
    updateClip,
    removeClip,
    moveClip,
  };
}
