"use client";

import { useState } from "react";
import type { Job } from "@/lib/api/types";
import { Button } from "@/components/ui/button";
import JobStatusCard from "./JobStatusCard";
import { useDownloadFolder } from "./useDownloadFolder";

type Props = {
  job: Job | null;
  busy: boolean;
  saving: boolean;
  output4k: boolean;
  validationError: string | null;
  requestError: string | null;
  onOutput4kChange: (value: boolean) => void;
  exportLabel?: string;
  onCancel: () => void;
  onExport: () => void;
  onDownload: (directory: string) => void;
};

/** 4K choice, export action, cancel confirmation, and the job status. */
export default function ExportBar({
  job,
  busy,
  saving,
  output4k,
  validationError,
  requestError,
  exportLabel = "Export compilation",
  onOutput4kChange,
  onCancel,
  onExport,
  onDownload,
}: Props) {
  const [confirming, setConfirming] = useState(false);
  const { folder, changeFolder } = useDownloadFolder();
  const showConfirm = confirming && busy;

  return (
    <div className="flex flex-col gap-2">
      <label className="flex cursor-pointer items-center justify-between gap-3 rounded-lg bg-muted/60 px-3 py-2 text-sm has-disabled:cursor-not-allowed has-disabled:opacity-60">
        <span>
          Export in 4K
          <span className="block text-xs text-muted-foreground">3840×2160; smaller videos are scaled up.</span>
        </span>
        <input
          type="checkbox"
          role="switch"
          className="peer sr-only"
          checked={output4k}
          disabled={busy}
          onChange={(event) => onOutput4kChange(event.target.checked)}
        />
        <span
          aria-hidden="true"
          className="relative h-5 w-9 shrink-0 rounded-full bg-foreground/20 transition-colors peer-checked:bg-primary peer-focus-visible:ring-3 peer-focus-visible:ring-ring/50 after:absolute after:top-0.5 after:left-0.5 after:size-4 after:rounded-full after:bg-foreground after:transition-transform peer-checked:after:translate-x-4 peer-checked:after:bg-primary-foreground"
        />
      </label>
      <Button type="button" size="lg" className="h-10 text-sm" onClick={onExport} disabled={busy}>
        {busy ? "Exporting…" : exportLabel}
      </Button>
      {busy && !showConfirm && (
        <Button type="button" variant="outline" onClick={() => setConfirming(true)}>
          Cancel export
        </Button>
      )}
      {showConfirm && (
        <div className="flex flex-col gap-2 rounded-lg border p-2">
          <p className="text-sm">Stop this export and delete the videos already downloaded?</p>
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
      {busy && (
        <p className="text-xs text-muted-foreground">Keep this page open until the export finishes.</p>
      )}

      {validationError && <p className="text-sm text-destructive">{validationError}</p>}
      {requestError && <p className="text-sm text-destructive">{requestError}</p>}

      {job && (
        <JobStatusCard
          job={job}
          saving={saving}
          folder={folder}
          onFolderChange={changeFolder}
          onDownload={onDownload}
        />
      )}
    </div>
  );
}
