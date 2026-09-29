"use client";

import { useEffect, useMemo, useState, type ReactNode } from "react";
import { fetchLogs, type CompilationLog, type VideoLog } from "@/lib/api";
import { formatSeconds } from "@/lib/time";
import { Input } from "@/components/ui/input";
import { cn } from "@/lib/utils";

const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

type Props = {
  active: boolean;
};

export default function LogsPanel({ active }: Props) {
  const [videos, setVideos] = useState<VideoLog[]>([]);
  const [compilations, setCompilations] = useState<CompilationLog[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [videoQuery, setVideoQuery] = useState("");
  const [compilationQuery, setCompilationQuery] = useState("");
  const [videoSort, setVideoSort] = useState<"used" | "last_used">("used");
  const [compilationSort, setCompilationSort] = useState<"newest" | "oldest">("newest");

  useEffect(() => {
    if (!active) return;
    let cancelled = false;
    fetchLogs()
      .then((logs) => {
        if (cancelled) return;
        setVideos(logs.videos);
        setCompilations(logs.compilations);
        setError(null);
      })
      .catch((err) => {
        if (cancelled) return;
        setError(err instanceof Error ? err.message : String(err));
      });
    return () => {
      cancelled = true;
    };
  }, [active]);

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

  const shownCompilations = useMemo(() => {
    const query = compilationQuery.trim().toLowerCase();
    const filtered = compilations.filter((item) =>
      query ? item.name.toLowerCase().includes(query) : true,
    );
    return filtered.sort((a, b) =>
      compilationSort === "newest" ? b.made.localeCompare(a.made) : a.made.localeCompare(b.made),
    );
  }, [compilations, compilationQuery, compilationSort]);

  return (
    <div className="flex flex-col gap-10">
      {error && <p className="text-sm text-destructive">{error}</p>}

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
              <th className="px-2 py-2 font-medium">
                <SortButton
                  active={videoSort === "last_used"}
                  onClick={() => setVideoSort("last_used")}
                >
                  Last used
                </SortButton>
              </th>
              <th className="px-2 py-2 text-right font-medium">
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
                      video.count > 0 && video.count === topCount
                        ? "bg-emerald-600"
                        : "bg-teal-700",
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

      <section className="flex flex-col gap-3">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <h2 className="flex items-center gap-2 text-base font-medium">
            Compilations
            <span className="rounded-full bg-muted px-2 py-0.5 text-xs text-muted-foreground">
              {compilations.length}
            </span>
          </h2>
          <Input
            value={compilationQuery}
            onChange={(event) => setCompilationQuery(event.target.value)}
            placeholder="Search compilations"
            aria-label="Search compilations"
            className="w-full sm:max-w-56"
          />
        </div>
        <LogTable
          empty={
            compilations.length === 0
              ? "Finished compilations are listed here."
              : "No compilations match that search."
          }
          isEmpty={shownCompilations.length === 0}
        >
          <thead>
            <tr className="text-left text-xs tracking-wide text-muted-foreground uppercase">
              <th className="px-2 py-2 font-medium">Name</th>
              <th className="px-2 py-2 font-medium">
                <SortButton
                  active
                  onClick={() =>
                    setCompilationSort((current) => (current === "newest" ? "oldest" : "newest"))
                  }
                >
                  Made
                </SortButton>
              </th>
              <th className="px-2 py-2 font-medium">Clips</th>
              <th className="px-2 py-2 font-medium">Length</th>
            </tr>
          </thead>
          <tbody>
            {shownCompilations.map((item) => (
              <tr key={`${item.name}-${item.made}`} className="border-t border-border">
                <td className="px-2 py-3">{item.name}</td>
                <td className="px-2 py-3 text-muted-foreground">{formatWhen(item.made)}</td>
                <td className="px-2 py-3 text-muted-foreground">{item.clips}</td>
                <td className="px-2 py-3 text-muted-foreground">
                  {formatSeconds(item.duration_seconds)}
                </td>
              </tr>
            ))}
          </tbody>
        </LogTable>
      </section>
    </div>
  );
}

function LogTable({
  children,
  empty,
  isEmpty,
}: {
  children: ReactNode;
  empty: string;
  isEmpty: boolean;
}) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full min-w-[720px] border-collapse text-sm">{children}</table>
      {isEmpty && <p className="px-2 py-6 text-sm text-muted-foreground">{empty}</p>}
    </div>
  );
}

function SortButton({
  active,
  onClick,
  children,
}: {
  active: boolean;
  onClick: () => void;
  children: ReactNode;
}) {
  return (
    <button type="button" onClick={onClick} className="uppercase">
      {children}
      {active ? " •" : ""}
    </button>
  );
}

function formatViews(count: number | null): string {
  if (count == null) return "—";
  if (count >= 1_000_000) {
    const millions = count / 1_000_000;
    const text = millions >= 10 ? millions.toFixed(0) : millions.toFixed(1);
    return `${text.replace(/\.0$/, "")}M`;
  }
  if (count >= 1_000) return `${Math.round(count / 1_000)}K`;
  return String(count);
}

function formatWhen(value: string | null): string {
  if (!value) return "—";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "—";
  const hours = String(date.getHours()).padStart(2, "0");
  const minutes = String(date.getMinutes()).padStart(2, "0");
  return `${date.getDate()} ${MONTHS[date.getMonth()]}, ${hours}:${minutes}`;
}
