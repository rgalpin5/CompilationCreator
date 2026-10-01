// @vitest-environment jsdom
import { act, renderHook } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { fetchChannelVideos } from "@/lib/api/channels";
import type { ChannelPage, Video } from "@/lib/api/types";
import { fetchUsage } from "@/lib/api/usage";
import { useChannelFeed } from "./useChannelFeed";

vi.mock("@/lib/api/channels", () => ({ fetchChannelVideos: vi.fn() }));
vi.mock("@/lib/api/usage", () => ({ fetchUsage: vi.fn() }));

const channels = vi.mocked(fetchChannelVideos);
const usage = vi.mocked(fetchUsage);
const URL_A = "https://www.youtube.com/@a";

function video(id: string, count = 0): Video {
  return {
    video_id: id,
    title: id,
    url: `https://www.youtube.com/watch?v=${id}`,
    thumbnail: null,
    duration_seconds: 60,
    channel: null,
    view_count: null,
    compilation_count: count,
  };
}

function page(ids: string[], hasMore: boolean, nextOffset: number): ChannelPage {
  return { videos: ids.map((id) => video(id)), has_more: hasMore, next_offset: nextOffset };
}

function deferred<T>() {
  let resolve!: (value: T) => void;
  let reject!: (reason: unknown) => void;
  const promise = new Promise<T>((res, rej) => {
    resolve = res;
    reject = rej;
  });
  return { promise, resolve, reject };
}

function ids(hook: { result: { current: ReturnType<typeof useChannelFeed> } }): string[] {
  return hook.result.current.videos.map((v) => v.video_id);
}

describe("useChannelFeed", () => {
  afterEach(() => {
    channels.mockReset();
    usage.mockReset();
  });

  it("loads the first page", async () => {
    channels.mockResolvedValue(page(["a", "b"], true, 2));
    const hook = renderHook(() => useChannelFeed());

    await act(() => hook.result.current.loadVideos(URL_A));

    expect(channels).toHaveBeenCalledWith(URL_A, 24, 0);
    expect(ids(hook)).toEqual(["a", "b"]);
    expect(hook.result.current.hasMore).toBe(true);
    expect(hook.result.current.loadingVideos).toBe(false);
    expect(hook.result.current.loadError).toBeNull();
  });

  it("shows a load error", async () => {
    channels.mockRejectedValue(new Error("Could not read that channel"));
    const hook = renderHook(() => useChannelFeed());

    await act(() => hook.result.current.loadVideos(URL_A));

    expect(hook.result.current.loadError).toBe("Could not read that channel");
    expect(hook.result.current.videos).toEqual([]);
    expect(hook.result.current.loadingVideos).toBe(false);
  });

  it("drops a response for a channel that is no longer selected", async () => {
    const stale = deferred<ChannelPage>();
    channels.mockReturnValueOnce(stale.promise).mockResolvedValueOnce(page(["new"], false, 1));
    const hook = renderHook(() => useChannelFeed());

    let first!: Promise<void>;
    act(() => {
      first = hook.result.current.loadVideos("https://www.youtube.com/@old");
    });
    await act(() => hook.result.current.loadVideos(URL_A));
    await act(async () => {
      stale.resolve(page(["old"], true, 1));
      await first;
    });

    expect(ids(hook)).toEqual(["new"]);
    expect(hook.result.current.hasMore).toBe(false);
  });

  it("drops an error for a channel that is no longer selected", async () => {
    const stale = deferred<ChannelPage>();
    channels.mockReturnValueOnce(stale.promise).mockResolvedValueOnce(page(["new"], false, 1));
    const hook = renderHook(() => useChannelFeed());

    let first!: Promise<void>;
    act(() => {
      first = hook.result.current.loadVideos("https://www.youtube.com/@old");
    });
    await act(() => hook.result.current.loadVideos(URL_A));
    await act(async () => {
      stale.reject(new Error("late failure"));
      await first;
    });

    expect(hook.result.current.loadError).toBeNull();
  });

  it("appends later pages without duplicates and stops at the end", async () => {
    channels
      .mockResolvedValueOnce(page(["a", "b"], true, 2))
      .mockResolvedValueOnce(page(["b", "c"], true, 4))
      .mockResolvedValueOnce(page([], true, 4));
    const hook = renderHook(() => useChannelFeed());
    await act(() => hook.result.current.loadVideos(URL_A));

    await act(() => hook.result.current.loadMore());
    expect(channels).toHaveBeenLastCalledWith(URL_A, 24, 2);
    expect(ids(hook)).toEqual(["a", "b", "c"]);
    expect(hook.result.current.hasMore).toBe(true);

    await act(() => hook.result.current.loadMore());
    expect(ids(hook)).toEqual(["a", "b", "c"]);
    // An empty page ends the list even when the server says there is more.
    expect(hook.result.current.hasMore).toBe(false);

    await act(() => hook.result.current.loadMore());
    expect(channels).toHaveBeenCalledTimes(3);
  });

  it("does nothing before a channel is loaded", async () => {
    const hook = renderHook(() => useChannelFeed());
    await act(() => hook.result.current.loadMore());
    expect(channels).not.toHaveBeenCalled();
  });

  it("ignores a second loadMore while one is running", async () => {
    const more = deferred<ChannelPage>();
    channels.mockResolvedValueOnce(page(["a"], true, 1)).mockReturnValueOnce(more.promise);
    const hook = renderHook(() => useChannelFeed());
    await act(() => hook.result.current.loadVideos(URL_A));

    let running!: Promise<void>;
    act(() => {
      running = hook.result.current.loadMore();
    });
    expect(hook.result.current.loadingMore).toBe(true);
    await act(() => hook.result.current.loadMore());
    expect(channels).toHaveBeenCalledTimes(2);

    await act(async () => {
      more.resolve(page(["b"], false, 2));
      await running;
    });
    expect(hook.result.current.loadingMore).toBe(false);
  });

  it("shows a load-more error and keeps the loaded videos", async () => {
    channels
      .mockResolvedValueOnce(page(["a"], true, 1))
      .mockRejectedValueOnce(new Error("Network down"));
    const hook = renderHook(() => useChannelFeed());
    await act(() => hook.result.current.loadVideos(URL_A));

    await act(() => hook.result.current.loadMore());

    expect(hook.result.current.moreError).toBe("Network down");
    expect(ids(hook)).toEqual(["a"]);
    expect(hook.result.current.loadingMore).toBe(false);
  });

  it("drops a later page when the channel changed meanwhile", async () => {
    const more = deferred<ChannelPage>();
    channels
      .mockResolvedValueOnce(page(["a"], true, 1))
      .mockReturnValueOnce(more.promise)
      .mockResolvedValueOnce(page(["x"], false, 1));
    const hook = renderHook(() => useChannelFeed());
    await act(() => hook.result.current.loadVideos(URL_A));

    let running!: Promise<void>;
    act(() => {
      running = hook.result.current.loadMore();
    });
    await act(() => hook.result.current.loadVideos("https://www.youtube.com/@b"));
    await act(async () => {
      more.reject(new Error("late"));
      await running;
    });

    expect(ids(hook)).toEqual(["x"]);
    expect(hook.result.current.moreError).toBeNull();
  });

  it("refreshes usage counts for the listed videos", async () => {
    channels.mockResolvedValue(page(["a", "b"], false, 2));
    usage.mockResolvedValue({ a: 3 });
    const hook = renderHook(() => useChannelFeed());
    await act(() => hook.result.current.loadVideos(URL_A));

    await act(() => hook.result.current.refreshUsage(() => true));

    expect(usage).toHaveBeenCalledWith(["a", "b"]);
    expect(hook.result.current.videos.map((v) => v.compilation_count)).toEqual([3, 0]);
  });

  it("skips a usage refresh that is no longer current", async () => {
    channels.mockResolvedValue(page(["a"], false, 1));
    usage.mockResolvedValue({ a: 3 });
    const hook = renderHook(() => useChannelFeed());
    await act(() => hook.result.current.loadVideos(URL_A));

    await act(() => hook.result.current.refreshUsage(() => false));

    expect(hook.result.current.videos[0]?.compilation_count).toBe(0);
  });

  it("ignores a failed usage request but not a non-error throw", async () => {
    const hook = renderHook(() => useChannelFeed());

    usage.mockRejectedValueOnce(new Error("offline"));
    await expect(hook.result.current.refreshUsage(() => true)).resolves.toBeUndefined();

    usage.mockRejectedValueOnce("odd");
    await expect(hook.result.current.refreshUsage(() => true)).rejects.toBe("odd");
  });
});
