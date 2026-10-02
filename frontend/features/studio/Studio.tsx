"use client";

import { useEffect, useMemo, useState } from "react";
import SiteHeader from "@/components/SiteHeader";
import { useAccount } from "@/features/account/AccountContext";
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
import { isDesktopEdition } from "@/lib/edition";
import { formatSeconds, parseTime, validateClips } from "@/lib/time";
import { cn } from "@/lib/utils";

/** The paid workspace: pick videos, cut them, export, and the usage logs. */
export default function Studio() {
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

  const totalSeconds = useMemo(
    () =>
      timeline.clips.reduce((sum, clip) => {
        const start = parseTime(clip.start) ?? 0;
        const end = parseTime(clip.end) ?? clip.duration_seconds ?? 0;
        return sum + Math.max(0, end - start);
      }, 0),
    [timeline.clips],
  );

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
      <SiteHeader
        nav={
          <div role="tablist" aria-label="Studio view" className="inline-flex rounded-lg bg-muted p-1">
            <ViewTab active={view === "editor"} onClick={() => setView("editor")}>
              Editor
            </ViewTab>
            <ViewTab active={view === "logs"} onClick={() => setView("logs")}>
              Logs
            </ViewTab>
          </div>
        }
        actions={<AccountMenu />}
      />

      <main className="mx-auto flex w-full max-w-7xl flex-col gap-6 p-4 md:p-6">
        <div className={view === "editor" ? "flex flex-col gap-6" : "hidden"}>
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
                <h2 className="font-heading text-base font-semibold">Channel videos</h2>
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

              <aside className="flex h-fit flex-col gap-4 rounded-xl bg-card p-4 ring-1 ring-border lg:sticky lg:top-18">
                <div className="flex items-baseline justify-between gap-3 border-b pb-3">
                  <h2 className="font-heading text-base font-semibold">
                    Timeline
                    <span className="ml-2 font-mono text-xs font-normal text-muted-foreground tabular-nums">
                      {timeline.clips.length} {timeline.clips.length === 1 ? "clip" : "clips"}
                    </span>
                  </h2>
                  <span className="font-mono text-sm text-primary tabular-nums" title="Total length">
                    {formatSeconds(totalSeconds)}
                  </span>
                </div>
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
              </aside>
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

function ViewTab({
  active,
  onClick,
  children,
}: {
  active: boolean;
  onClick: () => void;
  children: React.ReactNode;
}) {
  return (
    <button
      type="button"
      role="tab"
      aria-selected={active}
      onClick={onClick}
      className={cn(
        "rounded-sm px-3 py-1 text-sm transition-[color,background-color,box-shadow] duration-150",
        active ? "bg-background text-foreground shadow-sm" : "text-muted-foreground hover:text-foreground",
      )}
    >
      {children}
    </button>
  );
}

/** Who is signed in, with sign-out. The desktop app has no account. */
function AccountMenu() {
  const { account, signOut } = useAccount();
  if (isDesktopEdition || !account) return null;
  return (
    <div className="flex items-center gap-2">
      <span className="hidden max-w-48 truncate text-sm text-muted-foreground md:inline">
        {account.email}
      </span>
      <button
        type="button"
        onClick={() => void signOut()}
        className="rounded-md px-2 py-1 text-sm text-muted-foreground hover:bg-muted hover:text-foreground"
      >
        Sign out
      </button>
    </div>
  );
}
