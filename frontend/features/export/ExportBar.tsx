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
            The finished file is 3840×2160. A smaller video is scaled up to that size. The picture
            stays the same.
          </span>
        </span>
      </label>
      <Button type="button" onClick={onExport} disabled={busy}>
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
        <p className="text-sm text-muted-foreground">
          Clips download together, and matching videos are copied without re-encoding. A clip is
          re-encoded only when its picture or audio does not match the others. Keep this page open.
        </p>
      )}

      {validationError && (
        <p role="alert" className="text-sm text-destructive">
          {validationError}
        </p>
      )}
      {requestError && (
        <p role="alert" className="text-sm text-destructive">
          {requestError}
        </p>
      )}

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
