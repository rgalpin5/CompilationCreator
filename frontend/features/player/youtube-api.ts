"use client";

export type YTPlayer = {
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

/**
 * Load the YouTube IFrame API once per page.
 *
 * Resolves when ``window.YT.Player`` exists. Rejects with an ``Error`` when
 * the script fails or does not become ready within ten seconds.
 */
export function loadYouTubeApi(): Promise<void> {
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
