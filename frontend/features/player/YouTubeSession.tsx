"use client";

import { type ReactElement } from "react";
import { formatSeconds } from "@/lib/time";
import TrimBar from "./TrimBar";
import TrimControls from "./TrimControls";
import { clipBounds, trimTo, type TrimPatch } from "./trim";
import { useYouTubePlayer } from "./useYouTubePlayer";

type SessionProps = {
  videoId: string;
  title: string;
  start: string;
  end: string;
  durationSeconds: number | null;
  disabled?: boolean;
  onChange: (patch: TrimPatch) => void;
};

/**
 * The embedded player, trim bar, and intro and outro controls for one clip.
 *
 * If the IFrame API does not load, a plain embed is shown instead.
 */
export function YouTubeSession({
  videoId,
  title,
  start,
  end,
  durationSeconds,
  disabled,
  onChange,
}: SessionProps): ReactElement {
  const { containerRef, ready, apiFailed, playhead, knownDuration, readPlayhead, seek } =
    useYouTubePlayer(videoId);

  const synced = knownDuration != null;
  const duration =
    knownDuration != null
      ? knownDuration
      : durationSeconds != null && durationSeconds > 1
        ? durationSeconds
        : null;

  const { startSec, endSec } = clipBounds(start, end, duration);

  function commit(which: "start" | "end", point: number): void {
    const { patch } = trimTo(startSec, endSec, which, point, duration);
    if (patch) onChange(patch);
  }

  function cutHere(which: "start" | "end"): void {
    const time = readPlayhead();
    if (time == null) return;
    const { next, patch } = trimTo(startSec, endSec, which, time, duration);
    if (patch) onChange(patch);
    if (which === "start") seek(next.start);
    else seek(Math.max(next.start, next.end - 8));
  }

  const introRemoved = Math.max(0, startSec);
  const outroRemoved = duration != null ? Math.max(0, Math.floor(duration) - endSec) : null;
  const kept = Math.max(0, endSec - startSec);
  const canMark = ready && synced && !disabled;

  return (
    <>
      <div className="aspect-video w-full overflow-hidden rounded-lg bg-black [&_iframe]:size-full">
        {apiFailed ? (
          <iframe
            className="size-full"
            src={`https://www.youtube.com/embed/${encodeURIComponent(videoId)}?rel=0&modestbranding=1`}
            title={title}
            allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share"
            allowFullScreen
          />
        ) : (
          <div ref={containerRef} className="size-full" />
        )}
      </div>

      {duration != null && duration > 1 ? (
        <TrimBar
          duration={duration}
          start={startSec}
          end={endSec}
          playhead={Math.min(playhead, duration)}
          disabled={disabled}
          onSeek={seek}
          onChangeStart={(point) => commit("start", point)}
          onChangeEnd={(point) => commit("end", point)}
        />
      ) : null}

      <p className="text-xs text-muted-foreground tabular-nums">
        Playhead {formatSeconds(playhead)}
        {duration != null ? ` of ${formatSeconds(duration)}` : ""}
        {" · "}
        Keeping {formatSeconds(kept)}
        {introRemoved > 0 ? ` · intro cut ${formatSeconds(introRemoved)}` : ""}
        {outroRemoved != null && outroRemoved > 0 ? ` · outro cut ${formatSeconds(outroRemoved)}` : ""}
      </p>

      <TrimControls
        disabled={disabled}
        canMark={canMark}
        duration={duration}
        startSec={startSec}
        endSec={endSec}
        onSeek={seek}
        onCommit={commit}
        onCutHere={cutHere}
        onUseFull={(nextEnd) => onChange({ start: "00:00", end: nextEnd })}
      />
    </>
  );
}
