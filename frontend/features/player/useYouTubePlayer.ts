"use client";

import { useEffect, useLayoutEffect, useRef, useState, type RefObject } from "react";
import { loadYouTubeApi, type YTPlayer } from "./youtube-api";

/** The IFrame API throws Error or DOMException while a video is still cueing. */
function ignorePlayerTimingError(caught: unknown): void {
  if (caught instanceof Error || caught instanceof DOMException) return;
  throw caught;
}

export type YouTubePlayer = {
  /** Mount point for the player. Render it only while ``apiFailed`` is false. */
  containerRef: RefObject<HTMLDivElement | null>;
  ready: boolean;
  /** The IFrame API did not load, so the caller should show a plain embed. */
  apiFailed: boolean;
  playhead: number;
  /** The length the player reports for ``videoId``, once it is trustworthy. */
  knownDuration: number | null;
  /** The live playhead, or null until the player is showing ``videoId``. */
  readPlayhead: () => number | null;
  seek: (seconds: number) => void;
};

/**
 * One IFrame player that follows ``videoId``, plus its playhead and length.
 *
 * The player is created once and cued to each new id. Timing is ignored until
 * the player reports the current id with a plausible length, so a stale
 * reading from the previous video never reaches the trim controls.
 */
export function useYouTubePlayer(videoId: string): YouTubePlayer {
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

  return { containerRef, ready, apiFailed, playhead, knownDuration, readPlayhead, seek };
}
