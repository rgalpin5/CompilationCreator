"use client";

import { useState } from "react";
import { downloadHref, type Job, type JobStatus } from "@/lib/api";
import { Button, buttonVariants } from "@/components/ui/button";
import { cn } from "@/lib/utils";

type Props = {
  job: Job | null;
  busy: boolean;
  clipCount: number;
  output4k: boolean;
  validationError: string | null;
  requestError: string | null;
  onOutput4kChange: (value: boolean) => void;
  onCancel: () => void;
  onExport: () => void;
};

export default function ExportBar({
  job,
  busy,
  clipCount,
  output4k,
  validationError,
  requestError,
  onOutput4kChange,
  onCancel,
  onExport,
}: Props) {
  const [confirming, setConfirming] = useState(false);
  const showConfirm = confirming && busy;

  return (
    <div className="flex flex-col gap-2">
      <label className="flex items-start gap-2 text-sm">
        <input
          type="checkbox"
          className="mt-1"
          checked={output4k}
          disabled={busy}
          onChange={(event) => onOutput4kChange(event.target.checked)}
        />
        <span>
          Export in 4K
          <span className="block text-muted-foreground">
            The finished file is 4K only when every selected video is available
            in 4K. If any source is smaller, the export stops instead of
            upscaling it.
          </span>
        </span>
      </label>
      <Button type="button" onClick={onExport} disabled={busy}>
        {busy ? "Exporting…" : "Export mega video"}
      </Button>
      {busy && !showConfirm && (
        <Button type="button" variant="outline" onClick={() => setConfirming(true)}>
          Cancel export
        </Button>
      )}
      {showConfirm && (
        <div className="flex flex-col gap-2 rounded-lg border p-2">
          <p className="text-sm">
            Stop this export and delete the videos already downloaded?
          </p>
          <div className="flex gap-2">
            <Button
              type="button"
              variant="destructive"
              onClick={() => {
                setConfirming(false);
                onCancel();
              }}
            >
              Yes, cancel
            </Button>
            <Button type="button" variant="outline" onClick={() => setConfirming(false)}>
              Keep going
            </Button>
          </div>
        </div>
      )}
      {clipCount > 0 && clipCount < 4 && !busy && (
        <p className="text-sm text-muted-foreground">
          A full mega video is 4–8 videos. You can still export this shorter
          cut.
        </p>
      )}
      {busy && (
        <p className="text-sm text-muted-foreground">
          Clips download together, and matching videos are copied without
          re-encoding. A clip is re-encoded only when its picture or audio does
          not match the others. Keep this page open.
        </p>
      )}

      {validationError && (
        <p className="text-sm text-destructive">{validationError}</p>
      )}
      {requestError && (
        <p className="text-sm text-destructive">{requestError}</p>
      )}

      {job && (
        <div
          className={cn(
            "flex flex-col gap-1 rounded-lg px-3 py-2 text-sm",
            statusTone(job.status),
          )}
        >
          <p>
            Status: <span className="font-medium capitalize">{job.status}</span>
            {job.progress ? ` — ${job.progress}` : null}
          </p>
          {job.status === "cancelled" && (
            <p>Export cancelled. Partial downloads were deleted.</p>
          )}
          {job.status === "failed" && (
            <p className="text-destructive">
              {job.error || "Compilation failed."}
            </p>
          )}
          {job.status === "ready" && job.download_url && (
            <a
              href={downloadHref(job.download_url)}
              download
              className={buttonVariants({ variant: "outline" })}
            >
              Download MP4
            </a>
          )}
        </div>
      )}
    </div>
  );
}

function statusTone(status: JobStatus): string {
  if (status === "ready") return "bg-emerald-500/15 text-emerald-200";
  if (status === "failed") return "bg-red-500/15 text-red-200";
  if (status === "cancelled") return "bg-muted text-muted-foreground";
  return "bg-primary/10 text-foreground";
}
