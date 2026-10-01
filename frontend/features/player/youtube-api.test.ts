// @vitest-environment jsdom
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import type { loadYouTubeApi } from "./youtube-api";

const SRC = "https://www.youtube.com/iframe_api";

async function freshLoader(): Promise<typeof loadYouTubeApi> {
  vi.resetModules();
  return (await import("./youtube-api")).loadYouTubeApi;
}

function scripts(): HTMLScriptElement[] {
  return Array.from(document.querySelectorAll<HTMLScriptElement>(`script[src="${SRC}"]`));
}

describe("loadYouTubeApi", () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
    for (const tag of scripts()) tag.remove();
    delete window.YT;
    delete window.onYouTubeIframeAPIReady;
  });

  it("resolves at once when the API is already present", async () => {
    window.YT = { Player: vi.fn() as never };
    const load = await freshLoader();
    await expect(load()).resolves.toBeUndefined();
    expect(scripts()).toHaveLength(0);
  });

  it("adds the script once and resolves when YouTube calls back", async () => {
    const earlier = vi.fn();
    window.onYouTubeIframeAPIReady = earlier;
    const load = await freshLoader();

    const first = load();
    const second = load();
    expect(second).toBe(first);
    expect(scripts()).toHaveLength(1);

    window.onYouTubeIframeAPIReady?.();
    await expect(first).resolves.toBeUndefined();
    expect(earlier).toHaveBeenCalledTimes(1);
  });

  it("reuses a script tag that is already on the page", async () => {
    const tag = document.createElement("script");
    tag.src = SRC;
    document.head.appendChild(tag);
    const load = await freshLoader();

    const pending = load();
    expect(scripts()).toHaveLength(1);
    window.onYouTubeIframeAPIReady?.();
    await expect(pending).resolves.toBeUndefined();
  });

  it("rejects after ten seconds and allows a retry", async () => {
    const load = await freshLoader();

    const pending = load();
    const caught = expect(pending).rejects.toThrow("timeout");
    await vi.advanceTimersByTimeAsync(10000);
    await caught;

    expect(load()).not.toBe(pending);
  });

  it("rejects when the script fails to load", async () => {
    const load = await freshLoader();

    const pending = load();
    scripts()[0]?.onerror?.(new Event("error"));

    await expect(pending).rejects.toThrow("script");
  });
});
