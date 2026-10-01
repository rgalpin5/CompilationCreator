// @vitest-environment jsdom
import { act, renderHook } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import type { Video } from "@/lib/api/types";
import { useTimeline } from "./useTimeline";

function video(id: string, duration: number | null = 90): Video {
  return {
    video_id: id,
    title: `Video ${id}`,
    url: `https://www.youtube.com/watch?v=${id}`,
    thumbnail: null,
    duration_seconds: duration,
    channel: "Channel",
    view_count: 10,
    compilation_count: 0,
  };
}

function setup(ids: string[] = []) {
  const onEdit = vi.fn();
  const hook = renderHook(() => useTimeline(onEdit));
  for (const id of ids) {
    act(() => hook.result.current.addVideo(video(id)));
  }
  onEdit.mockClear();
  return { hook, onEdit };
}

function order(hook: ReturnType<typeof setup>["hook"]): string[] {
  return hook.result.current.clips.map((clip) => clip.video_id);
}

describe("useTimeline", () => {
  it("starts empty", () => {
    const { hook } = setup();
    expect(hook.result.current.clips).toEqual([]);
    expect(hook.result.current.cutIndex).toBe(0);
  });

  it("adds a video as a full-length clip", () => {
    const { hook, onEdit } = setup();
    act(() => hook.result.current.addVideo(video("a", 75)));
    expect(onEdit).toHaveBeenCalledTimes(1);
    expect(hook.result.current.clips[0]).toMatchObject({
      video_id: "a",
      title: "Video a",
      start: "00:00",
      end: "01:15",
      channel: "Channel",
      view_count: 10,
    });
  });

  it("removes a video that is added twice", () => {
    const { hook } = setup(["a", "b", "c"]);
    act(() => hook.result.current.setActiveIndex(2));
    act(() => hook.result.current.addVideo(video("a")));
    expect(order(hook)).toEqual(["b", "c"]);
    expect(hook.result.current.activeIndex).toBe(1);
  });

  it("updates one clip", () => {
    const { hook, onEdit } = setup(["a", "b"]);
    act(() => hook.result.current.updateClip(1, { start: "00:05" }));
    expect(onEdit).toHaveBeenCalledTimes(1);
    expect(hook.result.current.clips[0]?.start).toBe("00:00");
    expect(hook.result.current.clips[1]?.start).toBe("00:05");
  });

  it("keeps the selection on the same clip when an earlier one is removed", () => {
    const { hook } = setup(["a", "b", "c"]);
    act(() => hook.result.current.setActiveIndex(2));
    act(() => hook.result.current.removeClip(0));
    expect(order(hook)).toEqual(["b", "c"]);
    expect(hook.result.current.activeIndex).toBe(1);
  });

  it("moves the selection back when the last selected clip is removed", () => {
    const { hook } = setup(["a", "b", "c"]);
    act(() => hook.result.current.setActiveIndex(2));
    act(() => hook.result.current.removeClip(2));
    expect(hook.result.current.activeIndex).toBe(1);
  });

  it("leaves the selection alone when a later clip is removed", () => {
    const { hook } = setup(["a", "b", "c"]);
    act(() => hook.result.current.removeClip(2));
    expect(hook.result.current.activeIndex).toBe(0);
  });

  it("resets the selection when the only clip is removed", () => {
    const { hook } = setup(["a"]);
    act(() => hook.result.current.removeClip(0));
    expect(hook.result.current.clips).toEqual([]);
    expect(hook.result.current.activeIndex).toBe(0);
  });

  it("swaps a clip with its neighbour and follows the selection", () => {
    const { hook, onEdit } = setup(["a", "b", "c"]);
    act(() => hook.result.current.moveClip(0, 1));
    expect(order(hook)).toEqual(["b", "a", "c"]);
    expect(hook.result.current.activeIndex).toBe(1);
    expect(onEdit).toHaveBeenCalledTimes(1);

    act(() => hook.result.current.moveClip(2, -1));
    expect(order(hook)).toEqual(["b", "c", "a"]);
    expect(hook.result.current.activeIndex).toBe(2);
  });

  it("keeps an unrelated selection when two other clips swap", () => {
    const { hook } = setup(["a", "b", "c"]);
    act(() => hook.result.current.setActiveIndex(2));
    act(() => hook.result.current.moveClip(0, 1));
    expect(hook.result.current.activeIndex).toBe(2);
  });

  it("ignores moves past either end", () => {
    const { hook, onEdit } = setup(["a", "b"]);
    act(() => hook.result.current.moveClip(0, -1));
    act(() => hook.result.current.moveClip(1, 1));
    expect(order(hook)).toEqual(["a", "b"]);
    expect(onEdit).not.toHaveBeenCalled();
  });

  it("clamps the cut index to the last clip", () => {
    const { hook } = setup(["a", "b"]);
    act(() => hook.result.current.setActiveIndex(5));
    expect(hook.result.current.cutIndex).toBe(1);
  });
});
