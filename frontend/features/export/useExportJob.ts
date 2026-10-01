"use client";

import { useEffect, useState } from "react";
import {
  cancelCompilation,
  createCompilation,
  getCompilation,
  saveCompilation,
} from "@/lib/api/compilations";
import type { Job } from "@/lib/api/types";
import { errorMessage } from "@/lib/errors";
import { validateClips } from "@/lib/time";
import type { TimelineClip } from "@/features/timeline/types";

const POLL_MS = 2000;
// Consecutive failed status requests before the export is reported lost.
const MAX_POLL_FAILURES = 3;

export type ExportJobState = {
  job: Job | null;
  submitting: boolean;
  savingDownload: boolean;
  requestError: string | null;
  clearRequestError: () => void;
  jobActive: boolean;
  busy: boolean;
  cancelExport: () => Promise<void>;
  downloadExport: (directory: string) => Promise<void>;
  exportCompilation: () => Promise<void>;
};

type Args = {
  clips: TimelineClip[];
  output4k: boolean;
  setValidationError: (error: string | null) => void;
  refreshUsage: (isCurrent: () => boolean) => Promise<void>;
  onExported: () => void;
};

/** Create, poll, cancel, and save one export. Request failures stay in ``requestError``. */
export function useExportJob({
  clips,
  output4k,
  setValidationError,
  refreshUsage,
  onExported,
}: Args): ExportJobState {
  const [job, setJob] = useState<Job | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [savingDownload, setSavingDownload] = useState(false);
  const [requestError, setRequestError] = useState<string | null>(null);
  const [pollFailures, setPollFailures] = useState(0);

  const jobActive =
    job !== null &&
    job.status !== "ready" &&
    job.status !== "saved" &&
    job.status !== "failed" &&
    job.status !== "cancelled";
  const busy = submitting || jobActive;

  useEffect(() => {
    if (!job || !jobActive) return;
    let cancelled = false;
    const timer = setTimeout(async () => {
      let next: Job;
      try {
        next = await getCompilation(job.id);
      } catch (caught: unknown) {
        if (cancelled) return;
        // The export keeps running on the server, so one dropped request
        // should not end it here. Changing the count schedules the next poll.
        if (pollFailures + 1 < MAX_POLL_FAILURES) {
          setPollFailures(pollFailures + 1);
          return;
        }
        setRequestError(errorMessage(caught));
        setJob({ ...job, status: "failed", error: "Lost track of the job." });
        return;
      }
      if (cancelled) return;
      setPollFailures(0);
      setJob(next);
      if (next.status === "ready") await refreshUsage(() => !cancelled);
    }, POLL_MS);
    return () => {
      cancelled = true;
      clearTimeout(timer);
    };
  }, [job, jobActive, pollFailures, refreshUsage]);

  async function cancelExport(): Promise<void> {
    if (!job) return;
    try {
      setJob(await cancelCompilation(job.id));
    } catch (caught: unknown) {
      setRequestError(errorMessage(caught));
    }
  }

  async function downloadExport(directory: string): Promise<void> {
    if (!job || savingDownload) return;
    setRequestError(null);
    setSavingDownload(true);
    try {
      setJob(await saveCompilation(job.id, directory));
    } catch (caught: unknown) {
      setRequestError(errorMessage(caught));
    } finally {
      setSavingDownload(false);
    }
  }

  async function exportCompilation(): Promise<void> {
    if (busy) return;
    setRequestError(null);
    const error = validateClips(clips);
    setValidationError(error);
    if (error) return;

    setSubmitting(true);
    setJob(null);
    setPollFailures(0);
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
      onExported();
    } catch (caught: unknown) {
      setRequestError(errorMessage(caught));
    } finally {
      setSubmitting(false);
    }
  }

  return {
    job,
    submitting,
    savingDownload,
    requestError,
    clearRequestError: () => setRequestError(null),
    jobActive,
    busy,
    cancelExport,
    downloadExport,
    exportCompilation,
  };
}
