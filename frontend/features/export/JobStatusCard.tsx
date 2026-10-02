"use client";

import { useState } from "react";
import { compilationFileHref } from "@/lib/api/compilations";
import type { Job, JobStatus } from "@/lib/api/types";
import { Button, buttonVariants } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { cn } from "@/lib/utils";

type Props = {
  job: Job;
  saving: boolean;
  folder: string;
  onFolderChange: (value: string) => void;
  onDownload: (directory: string) => void;
};

/** Progress for the current export and the folder it will be saved into. */
export default function JobStatusCard({
  job,
  saving,
  folder,
  onFolderChange,
  onDownload,
}: Props) {
  // Keyed by job so a new export starts without the earlier "started" note.
  const [startedFor, setStartedFor] = useState<string | null>(null);
  return (
    <div className={cn("flex flex-col gap-1 rounded-lg px-3 py-2 text-sm tabular-nums", statusTone(job.status))}>
      <p>
        <span className="font-mono text-xs tracking-wider text-muted-foreground uppercase">Status</span>{" "}
        <span className="font-medium capitalize">{job.status}</span>
        {job.progress ? ` — ${job.progress}` : null}
      </p>
      {job.status === "cancelled" && <p>Export cancelled. Partial downloads were deleted.</p>}
      {job.status === "failed" && (
        <p className="text-destructive">{job.error || "Compilation failed."}</p>
      )}
      {job.status === "ready" && job.file_url && (
        <div className="flex flex-col gap-2 pt-1">
          <p className="text-muted-foreground">
            {startedFor === job.id
              ? "Your browser is downloading the MP4. If the download was interrupted, download it again within 10 minutes."
              : "Your browser saves the MP4. The server deletes its copy 10 minutes after the download finishes."}
          </p>
          <a
            href={compilationFileHref(job.file_url)}
            download
            className={buttonVariants({ variant: "outline" })}
            onClick={() => setStartedFor(job.id)}
          >
            Download MP4
          </a>
        </div>
      )}
      {job.status === "ready" && !job.file_url && (
        <div className="flex flex-col gap-2 pt-1">
          <label className="flex flex-col gap-1 text-sm">
            Save folder
            <Input
              value={folder}
              disabled={saving}
              aria-label="Save folder"
              placeholder="Downloads"
              onChange={(event) => onFolderChange(event.target.value)}
            />
          </label>
          <p className="text-muted-foreground">
            The video is saved here, then the working clips are deleted. Leave this blank to use
            your Downloads folder.
          </p>
          <Button type="button" variant="outline" disabled={saving} onClick={() => onDownload(folder)}>
            {saving ? "Saving…" : "Download MP4"}
          </Button>
        </div>
      )}
      {job.status === "saved" && job.saved_path && (
        <p>Saved to {job.saved_path}. Working files were deleted.</p>
      )}
    </div>
  );
}

function statusTone(status: JobStatus): string {
  if (status === "ready" || status === "saved") return "bg-keep/12 text-foreground ring-1 ring-keep/40";
  if (status === "failed") return "bg-destructive/12 text-foreground ring-1 ring-destructive/40";
  if (status === "cancelled") return "bg-muted text-muted-foreground";
  return "bg-primary/10 text-foreground ring-1 ring-primary/30";
}
