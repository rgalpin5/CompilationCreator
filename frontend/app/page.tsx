"use client";

import { useEffect, useMemo, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import PasswordGate from "@/features/auth/PasswordGate";
import ChannelForm from "@/features/channel/ChannelForm";
import { useChannelFeed } from "@/features/channel/useChannelFeed";
import VideoGrid from "@/features/channel/VideoGrid";
import CutStep from "@/features/cuts/CutStep";
import ExportBar from "@/features/export/ExportBar";
import { useExportJob } from "@/features/export/useExportJob";
import LogsPanel from "@/features/logs/LogsPanel";
import Timeline from "@/features/timeline/Timeline";
import { useTimeline } from "@/features/timeline/useTimeline";
import type { Video } from "@/lib/api/types";
import { validateClips } from "@/lib/time";
import { cn } from "@/lib/utils";

export default function Home() {
  return (
    <PasswordGate>
      <Editor />
    </PasswordGate>
  );
}

function Editor() {
  const [stage, setStage] = useState<"pick" | "cuts">("pick");
  const [view, setView] = useState<"editor" | "logs">("editor");
  const [output4k, setOutput4k] = useState(false);
  const [validationError, setValidationError] = useState<string | null>(null);

  const feed = useChannelFeed();
  const timeline = useTimeline(() => setValidationError(null));
  const exportJob = useExportJob({
    clips: timeline.clips,
    output4k,
    setValidationError,
    refreshUsage: feed.refreshUsage,
    onExported: () => setStage("pick"),
  });

  function addVideo(video: Video) {
    if (exportJob.busy) return;
    timeline.addVideo(video);
  }

  const selectedIds = useMemo(
    () => new Set(timeline.clips.map((clip) => clip.video_id)),
    [timeline.clips],
  );

  useEffect(() => {
    if (stage !== "cuts") return;
    document.getElementById("cut-step")?.scrollIntoView({ behavior: "smooth", block: "start" });
  }, [stage]);

  function openCuts() {
    if (exportJob.busy) return;
    exportJob.clearRequestError();
    const error = validateClips(timeline.clips);
    setValidationError(error);
    if (error) return;
    timeline.setActiveIndex(0);
    setStage("cuts");
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
            Stack videos into one compilation. Press export, then cut each intro and outro before
            the download starts.
          </p>
          <div className={stage === "pick" ? undefined : "hidden"}>
            <ChannelForm
              loading={feed.loadingVideos}
              error={feed.loadError}
              onSubmit={feed.loadVideos}
            />
          </div>

          {stage === "cuts" ? (
            <CutStep
              clips={timeline.clips}
              index={timeline.cutIndex}
              busy={exportJob.busy}
              job={exportJob.job}
              output4k={output4k}
              validationError={validationError}
              requestError={exportJob.requestError}
              onIndex={timeline.setActiveIndex}
              onChange={timeline.updateClip}
              onBack={() => setStage("pick")}
              onOutput4kChange={setOutput4k}
              onCancel={exportJob.cancelExport}
              onExport={exportJob.exportCompilation}
              saving={exportJob.savingDownload}
              onDownload={exportJob.downloadExport}
            />
          ) : (
            <div className="grid items-start gap-6 lg:grid-cols-[1fr_380px]">
              <section className="flex min-w-0 flex-col gap-3">
                <h2 className="text-sm font-medium">Channel videos</h2>
                <VideoGrid
                  videos={feed.videos}
                  selectedIds={selectedIds}
                  onSelect={addVideo}
                  loading={feed.loadingVideos}
                  hasMore={feed.hasMore}
                  loadingMore={feed.loadingMore}
                  moreError={feed.moreError}
                  onLoadMore={feed.loadMore}
                />
              </section>

              <Card className="h-fit shadow-sm lg:sticky lg:top-4">
                <CardHeader className="border-b">
                  <CardTitle>Timeline ({timeline.clips.length})</CardTitle>
                </CardHeader>
                <CardContent className="flex flex-col gap-4">
                  <Timeline
                    clips={timeline.clips}
                    disabled={exportJob.busy}
                    onRemove={timeline.removeClip}
                    onMove={timeline.moveClip}
                  />
                  <ExportBar
                    job={exportJob.job}
                    busy={exportJob.busy}
                    output4k={output4k}
                    onOutput4kChange={setOutput4k}
                    validationError={validationError}
                    requestError={exportJob.requestError}
                    onCancel={exportJob.cancelExport}
                    onExport={openCuts}
                    saving={exportJob.savingDownload}
                    onDownload={exportJob.downloadExport}
                  />
                </CardContent>
              </Card>
            </div>
          )}
        </div>
        <div className={view === "logs" ? undefined : "hidden"}>
          <LogsPanel active={view === "logs"} />
        </div>
      </main>
    </div>
  );
}
