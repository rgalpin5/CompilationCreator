"use client";

import { useMemo, useState } from "react";
import type { VideoLog } from "@/lib/api/types";
import { formatSeconds } from "@/lib/time";
import { Input } from "@/components/ui/input";
import { cn } from "@/lib/utils";
import { formatViews, formatWhen } from "./format";
import { LogTable, SortButton } from "./table";

type Props = {
  videos: VideoLog[];
};

/** Searchable table of videos and how often each was used. */
export default function VideoTable({ videos }: Props) {
  const [videoQuery, setVideoQuery] = useState("");
  const [videoSort, setVideoSort] = useState<"used" | "last_used">("used");

  const topCount = useMemo(
    () => videos.reduce((max, video) => Math.max(max, video.count), 0),
    [videos],
  );

  const shownVideos = useMemo(() => {
    const query = videoQuery.trim().toLowerCase();
    const filtered = videos.filter((video) => {
      if (!query) return true;
      return (
        video.title.toLowerCase().includes(query) ||
        (video.channel || "").toLowerCase().includes(query)
      );
    });
    return filtered.sort((a, b) => {
      if (videoSort === "last_used") {
        return (b.last_used || "").localeCompare(a.last_used || "");
      }
      return b.count - a.count || (b.last_used || "").localeCompare(a.last_used || "");
    });
  }, [videos, videoQuery, videoSort]);

  return (
    <section className="flex flex-col gap-3">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h2 className="flex items-center gap-2 text-base font-medium">
          Videos used
          <span className="rounded-full bg-muted px-2 py-0.5 text-xs text-muted-foreground">
            {videos.length}
          </span>
        </h2>
        <Input
          value={videoQuery}
          onChange={(event) => setVideoQuery(event.target.value)}
          placeholder="Search videos"
          aria-label="Search videos"
          className="w-full sm:max-w-56"
        />
      </div>
      <LogTable
        empty={
          videos.length === 0
            ? "Videos show up here after a compilation finishes."
            : "No videos match that search."
        }
        isEmpty={shownVideos.length === 0}
      >
        <thead>
          <tr className="text-left text-xs tracking-wide text-muted-foreground uppercase">
            <th className="px-2 py-2 font-medium">Title</th>
            <th className="px-2 py-2 font-medium">Channel</th>
            <th className="px-2 py-2 font-medium">Views</th>
            <th className="px-2 py-2 font-medium">Length</th>
            <th
              className="px-2 py-2 font-medium"
              aria-sort={videoSort === "last_used" ? "descending" : "none"}
            >
              <SortButton active={videoSort === "last_used"} onClick={() => setVideoSort("last_used")}>
                Last used
              </SortButton>
            </th>
            <th
              className="px-2 py-2 text-right font-medium"
              aria-sort={videoSort === "used" ? "descending" : "none"}
            >
              <SortButton active={videoSort === "used"} onClick={() => setVideoSort("used")}>
                Used
              </SortButton>
            </th>
          </tr>
        </thead>
        <tbody>
          {shownVideos.map((video) => (
            <tr key={video.video_id} className="border-t border-border">
              <td className="px-2 py-3">
                <div className="flex items-center gap-3">
                  <span className="h-10 w-16 shrink-0 overflow-hidden rounded bg-muted">
                    {video.thumbnail && (
                      // eslint-disable-next-line @next/next/no-img-element
                      <img src={video.thumbnail} alt="" className="h-full w-full object-cover" />
                    )}
                  </span>
                  <span className="line-clamp-2 max-w-xs">{video.title}</span>
                </div>
              </td>
              <td className="px-2 py-3 text-muted-foreground">{video.channel || "—"}</td>
              <td className="px-2 py-3 text-muted-foreground">{formatViews(video.view_count)}</td>
              <td className="px-2 py-3 text-muted-foreground">
                {video.duration_seconds == null ? "—" : formatSeconds(video.duration_seconds)}
              </td>
              <td className="px-2 py-3 text-muted-foreground">{formatWhen(video.last_used)}</td>
              <td className="px-2 py-3 text-right">
                <span
                  className={cn(
                    "inline-flex rounded-md px-2 py-1 text-xs font-medium text-white",
                    video.count > 0 && video.count === topCount ? "bg-emerald-600" : "bg-teal-700",
                  )}
                >
                  Used {video.count}x
                </span>
              </td>
            </tr>
          ))}
        </tbody>
      </LogTable>
    </section>
  );
}
