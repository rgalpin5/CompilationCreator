"use client";

import {
  useEffect,
  useRef,
  useState,
  type KeyboardEvent,
  type PointerEvent as ReactPointerEvent,
} from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import {
  defaultEnd,
  formatSeconds,
  parseTime,
  setTrimPoint,
} from "@/lib/time";

type YTPlayer = {
  destroy: () => void;
  cueVideoById: (args: { videoId: string }) => void;
  seekTo: (seconds: number, allowSeekAhead: boolean) => void;
  playVideo: () => void;
  getCurrentTime: () => number;
  getDuration: () => number;
  getVideoData: () => { video_id?: string };
};

type YTPlayerEvent = { target: YTPlayer };

interface YTNamespace {
  Player: new (
    element: HTMLElement,
    options: {
      videoId?: string;
      width?: string;
      height?: string;
      playerVars?: Record<string, string | number>;
      events?: {
        onReady?: (event: YTPlayerEvent) => void;
        onStateChange?: (event: YTPlayerEvent & { data: number }) => void;
      };
    },
  ) => YTPlayer;
}

declare global {
  interface Window {
    YT?: YTNamespace;
    onYouTubeIframeAPIReady?: () => void;
  }
}

let apiPromise: Promise<void> | null = null;

function loadYouTubeApi(): Promise<void> {
  if (window.YT?.Player) return Promise.resolve();
  if (!apiPromise) {
    apiPromise = new Promise((resolve, reject) => {
      const finish = (error?: Error) => {
        window.clearTimeout(timer);
        if (error) {
          apiPromise = null;
          reject(error);
          return;
        }
        resolve();
      };
      const timer = window.setTimeout(() => finish(new Error("timeout")), 10000);
      const previous = window.onYouTubeIframeAPIReady;
      window.onYouTubeIframeAPIReady = () => {
        previous?.();
        finish();
      };
      if (!document.querySelector('script[src="https://www.youtube.com/iframe_api"]')) {
        const tag = document.createElement("script");
        tag.src = "https://www.youtube.com/iframe_api";
        tag.onerror = () => finish(new Error("script"));
        document.head.appendChild(tag);
      }
    });
  }
  return apiPromise;
}

const SKIP_SECONDS = [
  { seconds: 10, label: "10s" },
  { seconds: 30, label: "30s" },
  { seconds: 60, label: "1 min" },
] as const;

type Props = {
  videoId: string;
  title: string;
  start: string;
  end: string;
  durationSeconds: number | null;
  disabled?: boolean;
  onChange: (patch: { start?: string; end?: string }) => void;
};

export default function ClipPlayer({
  videoId,
  title,
  start,
  end,
  durationSeconds,
  disabled,
  onChange,
}: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const playerRef = useRef<YTPlayer | null>(null);
  const videoIdRef = useRef(videoId);
  const loadedIdRef = useRef<string | null>(null);
  const trustedIdRef = useRef<string | null>(null);
  const switchedAtRef = useRef<number | null>(null);
  const lastDurationRef = useRef<number | null>(null);
  videoIdRef.current = videoId;

  const [ready, setReady] = useState(false);
  const [apiFailed, setApiFailed] = useState(false);
  const [meter, setMeter] = useState<{
    id: string;
    playhead: number;
    duration: number | null;
  }>({ id: videoId, playhead: 0, duration: null });
  if (meter.id !== videoId) {
    trustedIdRef.current = null;
    setMeter({ id: videoId, playhead: 0, duration: null });
  }

  const playhead = meter.id === videoId ? meter.playhead : 0;
  const knownDuration =
    meter.id === videoId && meter.duration != null && meter.duration > 1
      ? meter.duration
      : null;
  const synced = knownDuration != null;

  const duration =
    knownDuration != null
      ? knownDuration
      : durationSeconds != null && durationSeconds > 1
        ? durationSeconds
        : null;

  const startSec = parseTime(start) ?? 0;
  const endSec =
    parseTime(end) ??
    (duration != null ? Math.min(Math.floor(duration), startSec + 1) : startSec + 60);

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
      .catch(() => {
        if (!cancelled) setApiFailed(true);
      });

    return () => {
      cancelled = true;
      try {
        player?.destroy();
      } catch {
        // The iframe is already gone when the player was never ready.
      }
      mount?.remove();
      if (playerRef.current === player) playerRef.current = null;
    };
  }, []);

  function rememberTiming(player: YTPlayer) {
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
    } catch {
      // The player throws while a cue is still settling.
    }
  }

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
      } catch {
        // getCurrentTime throws while a new video is still cueing.
      }
    }, 250);
    return () => window.clearInterval(id);
  }, [ready]);

  function readPlayhead(): number | null {
    if (!ready || trustedIdRef.current !== videoId) return null;
    try {
      const time = playerRef.current?.getCurrentTime();
      if (typeof time === "number" && Number.isFinite(time)) return time;
    } catch {
      // Fall back to the last polled time.
    }
    return playhead;
  }

  function seek(seconds: number) {
    const player = playerRef.current;
    if (!player || !ready) return;
    const target = Math.max(0, seconds);
    try {
      player.seekTo(target, true);
      player.playVideo();
      setMeter((prev) =>
        prev.id === videoId ? { ...prev, playhead: target } : prev,
      );
    } catch {
      // Ignore seeks that land before the video metadata is ready.
    }
  }

  function commit(which: "start" | "end", point: number) {
    const next = setTrimPoint(startSec, endSec, which, point, duration);
    const patch: { start?: string; end?: string } = {};
    if (next.start !== startSec) patch.start = formatSeconds(next.start);
    if (next.end !== endSec) patch.end = formatSeconds(next.end);
    if (patch.start !== undefined || patch.end !== undefined) onChange(patch);
  }

  function cutHere(which: "start" | "end") {
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
  const outroRemoved =
    duration != null ? Math.max(0, Math.floor(duration) - endSec) : null;
  const kept = Math.max(0, endSec - startSec);
  const canMark = ready && synced && !disabled;

  return (
    <Card id="clip-player" className="scroll-mt-4 shadow-sm">
      <CardHeader className="border-b">
        <CardTitle className="line-clamp-2">{title}</CardTitle>
        <CardDescription>
          Play until the intro ends, then cut it. Jump to the ending and cut the outro the same way.
        </CardDescription>
      </CardHeader>
      <CardContent className="flex flex-col gap-3">
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
          {outroRemoved != null && outroRemoved > 0
            ? ` · outro cut ${formatSeconds(outroRemoved)}`
            : ""}
        </p>

        <div className="grid gap-2 sm:grid-cols-2">
          <div className="flex flex-col gap-2 rounded-lg bg-muted/50 p-2">
            <p className="text-xs font-medium">Intro</p>
            <div className="flex flex-wrap gap-1.5">
              <Button
                type="button"
                size="sm"
                variant="outline"
                disabled={!canMark}
                onClick={() => seek(0)}
              >
                Play
              </Button>
              <Button
                type="button"
                size="sm"
                disabled={!canMark}
                onClick={() => cutHere("start")}
              >
                Cut here
              </Button>
              {SKIP_SECONDS.map((skip) => (
                <Button
                  key={skip.label}
                  type="button"
                  size="sm"
                  variant="secondary"
                  disabled={disabled}
                  onClick={() => commit("start", startSec + skip.seconds)}
                >
                  Skip {skip.label}
                </Button>
              ))}
            </div>
          </div>
          <div className="flex flex-col gap-2 rounded-lg bg-muted/50 p-2">
            <p className="text-xs font-medium">Outro</p>
            <div className="flex flex-wrap gap-1.5">
              <Button
                type="button"
                size="sm"
                variant="outline"
                disabled={!canMark}
                onClick={() => seek(Math.max(0, (duration ?? endSec) - 25))}
              >
                Play
              </Button>
              <Button
                type="button"
                size="sm"
                disabled={!canMark}
                onClick={() => cutHere("end")}
              >
                Cut here
              </Button>
              {SKIP_SECONDS.map((skip) => (
                <Button
                  key={skip.label}
                  type="button"
                  size="sm"
                  variant="secondary"
                  disabled={disabled}
                  onClick={() => commit("end", endSec - skip.seconds)}
                >
                  Trim {skip.label}
                </Button>
              ))}
            </div>
          </div>
        </div>

        <div className="flex justify-end">
          <Button
            type="button"
            size="sm"
            variant="ghost"
            disabled={disabled || duration == null}
            onClick={() =>
              onChange({
                start: "00:00",
                end: defaultEnd(duration),
              })
            }
          >
            Use full video
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}

function TrimBar({
  duration,
  start,
  end,
  playhead,
  disabled,
  onSeek,
  onChangeStart,
  onChangeEnd,
}: {
  duration: number;
  start: number;
  end: number;
  playhead: number;
  disabled?: boolean;
  onSeek: (seconds: number) => void;
  onChangeStart: (seconds: number) => void;
  onChangeEnd: (seconds: number) => void;
}) {
  const trackRef = useRef<HTMLDivElement>(null);

  function secondsFromClientX(clientX: number) {
    const rect = trackRef.current?.getBoundingClientRect();
    if (!rect || rect.width <= 0) return 0;
    const ratio = Math.min(1, Math.max(0, (clientX - rect.left) / rect.width));
    return ratio * duration;
  }

  function beginDrag(
    event: ReactPointerEvent<HTMLElement>,
    apply: (seconds: number) => void,
  ) {
    if (disabled) return;
    event.preventDefault();
    event.stopPropagation();
    const target = event.currentTarget;
    target.setPointerCapture(event.pointerId);
    apply(secondsFromClientX(event.clientX));
    const onMove = (ev: PointerEvent) => apply(secondsFromClientX(ev.clientX));
    const onUp = (ev: PointerEvent) => {
      if (target.hasPointerCapture(ev.pointerId)) {
        target.releasePointerCapture(ev.pointerId);
      }
      target.removeEventListener("pointermove", onMove);
      target.removeEventListener("pointerup", onUp);
    };
    target.addEventListener("pointermove", onMove);
    target.addEventListener("pointerup", onUp);
  }

  function nudge(which: "start" | "end", key: string, shift: boolean) {
    const step = shift ? 5 : 1;
    const delta = key === "ArrowLeft" ? -step : key === "ArrowRight" ? step : 0;
    if (delta === 0) return false;
    if (which === "start") onChangeStart(start + delta);
    else onChangeEnd(end + delta);
    return true;
  }

  const startPct = (start / duration) * 100;
  const endPct = (end / duration) * 100;
  const playPct = (playhead / duration) * 100;

  return (
    <div className="flex flex-col gap-1">
      <div className="relative h-8">
        <div
          ref={trackRef}
          className="absolute inset-x-0 top-3 h-2 cursor-pointer rounded-full bg-foreground/15 touch-none"
          onPointerDown={(event) => beginDrag(event, onSeek)}
        >
          <div
            className="absolute inset-y-0 rounded-full bg-primary"
            style={{ left: `${startPct}%`, width: `${Math.max(0, endPct - startPct)}%` }}
          />
        </div>
        <div
          className="pointer-events-none absolute top-1 h-6 w-0.5 bg-foreground"
          style={{ left: `${playPct}%` }}
        />
        <Handle
          label="Intro cut"
          now={start}
          max={duration}
          percent={startPct}
          disabled={disabled}
          onPointerDown={(event) => beginDrag(event, onChangeStart)}
          onKeyDown={(event) => {
            if (nudge("start", event.key, event.shiftKey)) event.preventDefault();
          }}
        />
        <Handle
          label="Outro cut"
          now={end}
          max={duration}
          percent={endPct}
          disabled={disabled}
          onPointerDown={(event) => beginDrag(event, onChangeEnd)}
          onKeyDown={(event) => {
            if (nudge("end", event.key, event.shiftKey)) event.preventDefault();
          }}
        />
      </div>
      <div className="flex justify-between text-[11px] text-muted-foreground tabular-nums">
        <span>Start {formatSeconds(start)}</span>
        <span>{formatSeconds(end - start)} kept</span>
        <span>End {formatSeconds(end)}</span>
      </div>
    </div>
  );
}

function Handle({
  label,
  now,
  max,
  percent,
  disabled,
  onPointerDown,
  onKeyDown,
}: {
  label: string;
  now: number;
  max: number;
  percent: number;
  disabled?: boolean;
  onPointerDown: (event: ReactPointerEvent<HTMLButtonElement>) => void;
  onKeyDown: (event: KeyboardEvent<HTMLButtonElement>) => void;
}) {
  return (
    <button
      type="button"
      role="slider"
      aria-label={label}
      aria-valuemin={0}
      aria-valuemax={Math.floor(max)}
      aria-valuenow={Math.round(now)}
      aria-valuetext={formatSeconds(now)}
      disabled={disabled}
      onPointerDown={onPointerDown}
      onKeyDown={onKeyDown}
      className="absolute top-1 size-4 -translate-x-1/2 rounded-full border-2 border-primary bg-background shadow-sm touch-none disabled:opacity-50"
      style={{ left: `${percent}%` }}
    />
  );
}
