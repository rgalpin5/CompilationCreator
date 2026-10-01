import { describe, expect, it } from "vitest";
import { clipBounds, trimTo } from "./trim";

describe("clipBounds", () => {
  it("reads both times", () => {
    expect(clipBounds("00:10", "01:30", 600)).toEqual({ startSec: 10, endSec: 90 });
  });

  it("defaults a blank end to one second after the start when the length is known", () => {
    expect(clipBounds("00:10", "", 600)).toEqual({ startSec: 10, endSec: 11 });
  });

  it("keeps the default end inside a short video", () => {
    expect(clipBounds("00:00", "", 0.9)).toEqual({ startSec: 0, endSec: 0 });
  });

  it("defaults a blank end to one minute after the start when the length is unknown", () => {
    expect(clipBounds("", "", null)).toEqual({ startSec: 0, endSec: 60 });
  });
});

describe("trimTo", () => {
  it("returns only the side that moved", () => {
    expect(trimTo(10, 90, "start", 20, 600)).toEqual({
      next: { start: 20, end: 90 },
      patch: { start: "00:20" },
    });
  });

  it("returns a null patch when nothing changes", () => {
    expect(trimTo(10, 90, "end", 90, 600).patch).toBeNull();
  });

  it("keeps at least one second when the start is pushed past the end", () => {
    expect(trimTo(10, 90, "start", 200, 600)).toEqual({
      next: { start: 89, end: 90 },
      patch: { start: "01:29" },
    });
  });

  it("stops the end at the video length", () => {
    expect(trimTo(10, 90, "end", 700.6, 600)).toEqual({
      next: { start: 10, end: 600 },
      patch: { end: "10:00" },
    });
  });
});
