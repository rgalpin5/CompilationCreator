"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import {
  cancelCompilation,
  createCompilation,
  fetchChannelVideos,
  fetchUsage,
  getCompilation,
  type Job,
  type Video,
} from "@/lib/api";
import {
  defaultEnd,
  formatSeconds,
  parseTime,
  validateClips,
  MAX_CLIPS,
} from "@/lib/time";
import ChannelForm from "@/components/ChannelForm";
import VideoGrid from "@/components/VideoGrid";
import Timeline, { type TimelineClip } from "@/components/Timeline";
import ExportBar from "@/components/ExportBar";
import LogsPanel from "@/components/LogsPanel";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { cn } from "@/lib/utils";

const POLL_MS = 2000;

export default function Home() {
  const [videos, setVideos] = useState<Video[]>([]);
  const [loadingVideos, setLoadingVideos] = useState(false);
  const [loadError, setLoadError] = useState<string | null>(null);

  const [clips, setClips] = useState<TimelineClip[]>([]);
  const [output4k, setOutput4k] = useState(false);

  const [job, setJob] = useState<Job | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [validationError, setValidationError] = useState<string | null>(null);
  const [requestError, setRequestError] = useState<string | null>(null);
  const [view, setView] = useState<"editor" | "logs">("editor");

  const jobActive =
    job !== null &&
    job.status !== "ready" &&
    job.status !== "failed" &&
    job.status !== "cancelled";
  const busy = submitting || jobActive;

  const selectedIds = useMemo(
    () => new Set(clips.map((c) => c.video_id)),
    [clips],
  );
  const videoIdsRef = useRef<string[]>([]);
  videoIdsRef.current = videos.map((video) => video.video_id);

  const totalLength = useMemo(() => {
    let total = 0;
    for (const clip of clips) {
      const start = parseTime(clip.start);
      const end = parseTime(clip.end);
      if (start === null || end === null || end <= start) return null;
      total += end - start;
    }
    return formatSeconds(total);
  }, [clips]);

  useEffect(() => {
    if (!job || !jobActive) return;
    let cancelled = false;
    const timer = setTimeout(async () => {
      try {
        const next = await getCompilation(job.id);
        if (cancelled) return;
        setJob(next);
        if (next.status !== "ready") return;
        try {
          const counts = await fetchUsage(videoIdsRef.current);
          if (cancelled) return;
          setVideos((prev) =>
            prev.map((video) => ({
              ...video,
              compilation_count: counts[video.video_id] ?? video.compilation_count,
            })),
          );
        } catch {
          // The export finished. A missed count refresh can wait for the next channel load.
        }
      } catch (err) {
        if (cancelled) return;
        setRequestError(err instanceof Error ? err.message : String(err));
        setJob({ ...job, status: "failed", error: "Lost track of the job." });
      }
    }, POLL_MS);
    return () => {
      cancelled = true;
      clearTimeout(timer);
    };
  }, [job, jobActive]);

  async function loadVideos(url: string) {
    setLoadingVideos(true);
    setLoadError(null);
    try {
      setVideos(await fetchChannelVideos(url, 24));
    } catch (err) {
      setLoadError(err instanceof Error ? err.message : String(err));
    } finally {
      setLoadingVideos(false);
    }
  }

  function addVideo(video: Video) {
    if (busy) return;
    setValidationError(null);
    setClips((prev) =>
      prev.some((c) => c.video_id === video.video_id)
        ? prev.filter((c) => c.video_id !== video.video_id)
        : [
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
          ],
    );
  }

  function updateClip(index: number, patch: Partial<TimelineClip>) {
    setValidationError(null);
    setClips((prev) =>
      prev.map((c, i) => (i === index ? { ...c, ...patch } : c)),
    );
  }

  function removeClip(index: number) {
    setValidationError(null);
    setClips((prev) => prev.filter((_, i) => i !== index));
  }

  function moveClip(index: number, direction: -1 | 1) {
    setValidationError(null);
    setClips((prev) => {
      const target = index + direction;
      if (target < 0 || target >= prev.length) return prev;
      const next = [...prev];
      [next[index], next[target]] = [next[target], next[index]];
      return next;
    });
  }

  async function cancelExport() {
    if (!job) return;
    try {
      setJob(await cancelCompilation(job.id));
    } catch (err) {
      setRequestError(err instanceof Error ? err.message : String(err));
    }
  }

  async function exportCompilation() {
    if (busy) return;
    setRequestError(null);
    const error = validateClips(clips);
    setValidationError(error);
    if (error) return;

    setSubmitting(true);
    setJob(null);
    try {
      const created = await createCompilation(
        clips.map((c, i) => ({
          video_id: c.video_id,
          title: c.title,
          start: c.start.trim(),
          end: c.end.trim(),
          order: i,
          channel: c.channel,
          view_count: c.view_count,
          duration_seconds: c.duration_seconds,
          thumbnail: c.thumbnail,
        })),
        output4k,
      );
      setJob(created);
    } catch (err) {
      setRequestError(err instanceof Error ? err.message : String(err));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="flex flex-1 flex-col">
      <header className="border-b bg-card">
        <div className="mx-auto flex w-full max-w-7xl items-center px-4 py-3 md:px-6">
          <div className="inline-flex rounded-lg bg-muted p-1">
            <button
              type="button"
              aria-pressed={view === "editor"}
              onClick={() => setView("editor")}
              className={cn(
                "rounded-md px-3 py-1 text-sm",
                view === "editor" ? "bg-background shadow-sm" : "text-muted-foreground",
              )}
            >
              CompCreator
            </button>
            <button
              type="button"
              aria-pressed={view === "logs"}
              onClick={() => setView("logs")}
              className={cn(
                "rounded-md px-3 py-1 text-sm",
                view === "logs" ? "bg-background shadow-sm" : "text-muted-foreground",
              )}
            >
              Logs
            </button>
          </div>
        </div>
      </header>

      <main className="mx-auto flex w-full max-w-7xl flex-col gap-6 p-4 md:p-6">
      <div className={view === "editor" ? "flex flex-col gap-6" : "hidden"}>
      <p className="text-sm text-muted-foreground">
        Stack 4–8 videos, about 20–30 minutes each, into one mega video.
      </p>
      <ChannelForm
        loading={loadingVideos}
        error={loadError}
        onSubmit={loadVideos}
      />

      <div className="grid items-start gap-6 lg:grid-cols-[1fr_380px]">
        <section className="flex flex-col gap-3">
          <h2 className="text-sm font-medium">Channel videos</h2>
          <VideoGrid
            videos={videos}
            selectedIds={selectedIds}
            onSelect={addVideo}
          />
        </section>

        <Card className="h-fit shadow-sm lg:sticky lg:top-4">
          <CardHeader className="border-b">
            <CardTitle>
              Timeline ({clips.length} of {MAX_CLIPS})
              {clips.length > 0 && totalLength ? ` · ${totalLength}` : ""}
            </CardTitle>
          </CardHeader>
          <CardContent className="flex flex-col gap-4">
            <Timeline
              clips={clips}
              disabled={busy}
              onChange={updateClip}
              onRemove={removeClip}
              onMove={moveClip}
            />
            <ExportBar
              job={job}
              busy={busy}
              clipCount={clips.length}
              output4k={output4k}
              onOutput4kChange={setOutput4k}
              validationError={validationError}
              requestError={requestError}
              onCancel={cancelExport}
              onExport={exportCompilation}
            />
          </CardContent>
        </Card>
      </div>
      </div>
      <div className={view === "logs" ? undefined : "hidden"}>
        <LogsPanel active={view === "logs"} />
      </div>
      </main>
    </div>
  );
}
