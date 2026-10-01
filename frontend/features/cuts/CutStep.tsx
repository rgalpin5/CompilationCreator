"use client";

import { Button } from "@/components/ui/button";
import TrimStrip from "@/components/TrimStrip";
import ExportBar from "@/features/export/ExportBar";
import ClipPlayer from "@/features/player/ClipPlayer";
import type { TimelineClip } from "@/features/timeline/types";
import type { Job } from "@/lib/api/types";
import { formatSeconds, parseTime } from "@/lib/time";
import { cn } from "@/lib/utils";

type Props = {
  clips: TimelineClip[];
  index: number;
  busy: boolean;
  job: Job | null;
  output4k: boolean;
  validationError: string | null;
  requestError: string | null;
  onIndex: (index: number) => void;
  onChange: (index: number, patch: Partial<TimelineClip>) => void;
  onBack: () => void;
  onOutput4kChange: (value: boolean) => void;
  onCancel: () => void;
  onExport: () => void;
  saving: boolean;
  onDownload: (directory: string) => void;
};

/** The cut screen: clip list, player, and the export bar. */
export default function CutStep({
  clips,
  index,
  busy,
  job,
  output4k,
  validationError,
  requestError,
  onIndex,
  onChange,
  onBack,
  onOutput4kChange,
  onCancel,
  onExport,
  saving,
  onDownload,
}: Props) {
  const clip = clips[index];
  if (!clip) return null;

  return (
    <div id="cut-step" className="flex scroll-mt-18 flex-col gap-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="font-heading text-xl font-semibold">Cut intros and outros</h2>
          <p className="font-mono text-xs text-muted-foreground tabular-nums">
            Clip {index + 1} / {clips.length}
          </p>
        </div>
        <Button type="button" variant="outline" onClick={onBack} disabled={busy}>
          Back to timeline
        </Button>
      </div>

      <div className="grid items-start gap-6 lg:grid-cols-[minmax(0,1fr)_380px]">
        <div className="flex min-w-0 flex-col gap-3">
          <ClipPlayer
            videoId={clip.video_id}
            title={clip.title}
            start={clip.start}
            end={clip.end}
            durationSeconds={clip.duration_seconds ?? null}
            disabled={busy}
            onChange={(patch) => onChange(index, patch)}
          />
          <div className="flex gap-2">
            <Button
              type="button"
              variant="outline"
              disabled={busy || index === 0}
              onClick={() => onIndex(index - 1)}
            >
              Previous video
            </Button>
            <Button
              type="button"
              variant="outline"
              disabled={busy || index === clips.length - 1}
              onClick={() => onIndex(index + 1)}
            >
              Next video
            </Button>
          </div>
        </div>

        <aside className="flex h-fit flex-col gap-4 rounded-xl bg-card p-4 ring-1 ring-border lg:sticky lg:top-18">
          <h2 className="border-b pb-3 font-heading text-base font-semibold">Clips</h2>
            <ol className="flex flex-col gap-2">
              {clips.map((item, i) => {
                const start = parseTime(item.start) ?? 0;
                const end = parseTime(item.end);
                const outro =
                  item.duration_seconds != null && end != null
                    ? Math.max(0, Math.floor(item.duration_seconds) - end)
                    : 0;
                return (
                  <li key={item.video_id}>
                    <button
                      type="button"
                      disabled={busy}
                      onClick={() => onIndex(i)}
                      aria-current={i === index ? "true" : undefined}
                      className={cn(
                        "flex w-full flex-col gap-1.5 rounded-lg px-2.5 py-2 text-left text-sm",
                        i === index ? "bg-primary/12 ring-1 ring-primary/70" : "hover:bg-muted",
                      )}
                    >
                      <span className="line-clamp-2">
                        <span className="mr-1.5 font-mono text-xs text-muted-foreground">{i + 1}</span>
                        {item.title}
                      </span>
                      {item.duration_seconds != null && (
                        <TrimStrip
                          duration={item.duration_seconds}
                          start={start}
                          end={end ?? item.duration_seconds}
                        />
                      )}
                      <span className="font-mono text-[11px] text-muted-foreground tabular-nums">
                        {start > 0 ? `${formatSeconds(start)} intro` : "No intro"}
                        {" · "}
                        {outro > 0 ? `${formatSeconds(outro)} outro` : "No outro"}
                      </span>
                    </button>
                  </li>
                );
              })}
            </ol>
            <ExportBar
              job={job}
              busy={busy}
              output4k={output4k}
              exportLabel="Start export"
              onOutput4kChange={onOutput4kChange}
              validationError={validationError}
              requestError={requestError}
              onCancel={onCancel}
              onExport={onExport}
              saving={saving}
              onDownload={onDownload}
            />
        </aside>
      </div>
    </div>
  );
}
