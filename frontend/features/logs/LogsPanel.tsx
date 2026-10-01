"use client";

import { useEffect, useState, type ReactElement } from "react";
import { fetchLogs } from "@/lib/api/usage";
import type { CompilationLog, VideoLog } from "@/lib/api/types";
import { errorMessage } from "@/lib/errors";
import CompilationTable from "./CompilationTable";
import VideoTable from "./VideoTable";

type Props = {
  active: boolean;
};

/** Fetch the usage log once while this panel is visible and show both tables. */
export default function LogsPanel({ active }: Props): ReactElement {
  const [videos, setVideos] = useState<VideoLog[]>([]);
  const [compilations, setCompilations] = useState<CompilationLog[]>([]);
  const [error, setError] = useState<string | null>(null);

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
      .catch((caught: unknown) => {
        if (cancelled) return;
        setError(errorMessage(caught));
      });
    return () => {
      cancelled = true;
    };
  }, [active]);

  return (
    <div className="flex flex-col gap-10">
      {error && (
        <p role="alert" className="text-sm text-destructive">
          {error}
        </p>
      )}
      <VideoTable videos={videos} />
      <CompilationTable compilations={compilations} />
    </div>
  );
}
