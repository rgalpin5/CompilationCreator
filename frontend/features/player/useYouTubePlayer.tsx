"use client";

import { useEffect, useLayoutEffect, useRef, useState, type ReactElement } from "react";
import { formatSeconds, parseTime, setTrimPoint } from "@/lib/time";
import TrimBar from "./TrimBar";
import TrimControls from "./TrimControls";
import { loadYouTubeApi, type YTPlayer } from "./youtube-api";

/** The IFrame API throws Error or DOMException while a video is still cueing. */
function ignorePlayerTimingError(caught: unknown): void {
  if (caught instanceof Error || caught instanceof DOMException) return;
  throw caught;
}

type SessionProps = {
  videoId: string;
  title: string;
  start: string;
  end: string;
  durationSeconds: number | null;
  disabled?: boolean;
  onChange: (patch: { start?: string; end?: string }) => void;
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
  const containerRef = useRef<HTMLDivElement>(null);
  const playerRef = useRef<YTPlayer | null>(null);
  const videoIdRef = useRef(videoId);
  const loadedIdRef = useRef<string | null>(null);
  const trustedIdRef = useRef<string | null>(null);
  const switchedAtRef = useRef<number | null>(null);
  const lastDurationRef = useRef<number | null>(null);
  useLayoutEffect(() => {
    videoIdRef.current = videoId;
  }, [videoId]);

  const [ready, setReady] = useState(false);
  const [apiFailed, setApiFailed] = useState(false);
  const [meter, setMeter] = useState<{
    id: string;
    playhead: number;
    duration: number | null;
  }>({ id: videoId, playhead: 0, duration: null });
  if (meter.id !== videoId) {
    setMeter({ id: videoId, playhead: 0, duration: null });
  }

  useLayoutEffect(() => {
    trustedIdRef.current = null;
  }, [videoId]);

  const playhead = meter.id === videoId ? meter.playhead : 0;
  const knownDuration =
    meter.id === videoId && meter.duration != null && meter.duration > 1 ? meter.duration : null;
  const synced = knownDuration != null;

  const duration =
    knownDuration != null
      ? knownDuration
      : durationSeconds != null && durationSeconds > 1
        ? durationSeconds
        : null;

  function rememberTiming(player: YTPlayer): void {
    try {
      const id = player.getVideoData?.().video_id;
      if (!id || id !== videoIdRef.current) return;
      const length = player.getDuration();
      if (!Number.isFinite(length) || length <= 1) return;
      trustedIdRef.current = id;
      switchedAtRef.current = null;
      lastDurationRef.current = length;
      const time = player.getCurrentTime();
      setMeter({
        id,
        playhead: Number.isFinite(time) ? time : 0,
        duration: length,
      });
    } catch (caught: unknown) {
      ignorePlayerTimingError(caught);
    }
  }

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;
    let cancelled = false;
    let player: YTPlayer | null = null;
    let mount: HTMLDivElement | null = null;

    loadYouTubeApi()
      .then(() => {
        if (cancelled || !container || !window.YT) return;
        mount = document.createElement("div");
        mount.className = "size-full";
        container.appendChild(mount);
        const initialId = videoIdRef.current;
        loadedIdRef.current = initialId;
        player = new window.YT.Player(mount, {
          videoId: initialId,
          width: "100%",
          height: "100%",
          playerVars: {
            rel: 0,
            modestbranding: 1,
            playsinline: 1,
            origin: window.location.origin,
          },
          events: {
            onReady: (event) => {
              if (cancelled) {
                event.target.destroy();
                return;
              }
              playerRef.current = event.target;
              const id = videoIdRef.current;
              if (loadedIdRef.current !== id) {
                loadedIdRef.current = id;
                trustedIdRef.current = null;
                event.target.cueVideoById({ videoId: id });
              } else {
                rememberTiming(event.target);
              }
              setReady(true);
            },
            onStateChange: (event) => {
              if (cancelled) return;
              // 1 playing, 2 paused, 5 cued. Duration is meaningful in these states.
              if (event.data !== 1 && event.data !== 2 && event.data !== 5) return;
              rememberTiming(event.target);
            },
          },
        });
        playerRef.current = player;
      })
      .catch((_caught: unknown) => {
        // Script errors and timeouts both fall back to a plain embed.
        if (!cancelled) setApiFailed(true);
      });

    return () => {
      cancelled = true;
      try {
        player?.destroy();
      } catch (caught: unknown) {
        ignorePlayerTimingError(caught);
      }
      mount?.remove();
      if (playerRef.current === player) playerRef.current = null;
    };
  }, []);

  useEffect(() => {
    if (!ready || !playerRef.current) return;
    if (loadedIdRef.current === videoId) return;
    loadedIdRef.current = videoId;
    trustedIdRef.current = null;
    switchedAtRef.current = Date.now();
    playerRef.current.cueVideoById({ videoId });
  }, [videoId, ready]);

  useEffect(() => {
    if (!ready) return;
    const id = window.setInterval(() => {
      const player = playerRef.current;
      if (!player) return;
      try {
        const playingId = player.getVideoData?.().video_id;
        if (!playingId || playingId !== videoIdRef.current) return;
        const time = player.getCurrentTime();
        const length = player.getDuration();
        if (!Number.isFinite(time) || !Number.isFinite(length) || length <= 1) return;
        const switchedAt = switchedAtRef.current;
        const previous = lastDurationRef.current;
        if (
          switchedAt &&
          previous != null &&
          Math.abs(length - previous) < 0.5 &&
          Date.now() - switchedAt < 1500
        ) {
          return;
        }
        trustedIdRef.current = playingId;
        switchedAtRef.current = null;
        lastDurationRef.current = length;
        setMeter({ id: playingId, playhead: time, duration: length });
      } catch (caught: unknown) {
        ignorePlayerTimingError(caught);
      }
    }, 250);
    return () => window.clearInterval(id);
  }, [ready]);

  function readPlayhead(): number | null {
    if (!ready || trustedIdRef.current !== videoId) return null;
    try {
      const time = playerRef.current?.getCurrentTime();
      if (typeof time === "number" && Number.isFinite(time)) return time;
    } catch (caught: unknown) {
      ignorePlayerTimingError(caught);
    }
    return playhead;
  }

  function seek(seconds: number): void {
    const player = playerRef.current;
    if (!player || !ready) return;
    const target = Math.max(0, seconds);
    try {
      player.seekTo(target, true);
      player.playVideo();
      setMeter((prev) => (prev.id === videoId ? { ...prev, playhead: target } : prev));
    } catch (caught: unknown) {
      ignorePlayerTimingError(caught);
    }
  }

  const startSec = parseTime(start) ?? 0;
  const endSec =
    parseTime(end) ??
    (duration != null ? Math.min(Math.floor(duration), startSec + 1) : startSec + 60);

  function commit(which: "start" | "end", point: number): void {
    const next = setTrimPoint(startSec, endSec, which, point, duration);
    const patch: { start?: string; end?: string } = {};
    if (next.start !== startSec) patch.start = formatSeconds(next.start);
    if (next.end !== endSec) patch.end = formatSeconds(next.end);
    if (patch.start !== undefined || patch.end !== undefined) onChange(patch);
  }

  function cutHere(which: "start" | "end"): void {
    const time = readPlayhead();
    if (time == null) return;
    const next = setTrimPoint(startSec, endSec, which, time, duration);
    const patch: { start?: string; end?: string } = {};
    if (next.start !== startSec) patch.start = formatSeconds(next.start);
    if (next.end !== endSec) patch.end = formatSeconds(next.end);
    if (patch.start !== undefined || patch.end !== undefined) onChange(patch);
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
