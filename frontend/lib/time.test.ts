import { describe, expect, it } from "vitest";

import {
  defaultEnd,
  formatSeconds,
  parseTime,
  setTrimPoint,
  validateClips,
} from "./time";

describe("parseTime", () => {
  it("reads mm:ss and hh:mm:ss", () => {
    expect(parseTime("1:05")).toBe(65);
    expect(parseTime(" 01:02:03 ")).toBe(3723);
    expect(parseTime("00:00")).toBe(0);
  });

  it("rejects a clock that is not mm:ss or hh:mm:ss", () => {
    expect(parseTime("15")).toBeNull();
    expect(parseTime("1:60")).toBeNull();
    expect(parseTime("60:00")).toBeNull();
    expect(parseTime("1:2:03")).toBeNull();
  });
});

describe("formatSeconds", () => {
  it("pads minutes under an hour and leaves hours unpadded", () => {
    expect(formatSeconds(0)).toBe("00:00");
    expect(formatSeconds(65.9)).toBe("01:05");
    expect(formatSeconds(3723)).toBe("1:02:03");
  });

  it("treats a negative duration as zero", () => {
    expect(formatSeconds(-4)).toBe("00:00");
  });
});

describe("validateClips", () => {
  it("requires one clip and an end after the start", () => {
    expect(validateClips([])).toBe("Add at least one clip to the timeline.");
    expect(validateClips([{ title: "A", start: "nope", end: "0:10" }])).toBe(
      'Clip 1 ("A"): start "nope" must be mm:ss or hh:mm:ss.',
    );
    expect(validateClips([{ title: "A", start: "0:10", end: "later" }])).toBe(
      'Clip 1 ("A"): end "later" must be mm:ss or hh:mm:ss.',
    );
    expect(validateClips([{ title: "A", start: "0:20", end: "0:10" }])).toBe(
      'Clip 1 ("A"): end must be after start.',
    );
    expect(validateClips([{ title: "A", start: "0:10", end: "0:40" }])).toBeNull();
  });
});

describe("defaultEnd", () => {
  it("uses the full length when it is known", () => {
    expect(defaultEnd(90)).toBe("01:30");
  });

  it("uses thirty minutes when the length is missing or not positive", () => {
    expect(defaultEnd(null)).toBe("30:00");
    expect(defaultEnd(0)).toBe("30:00");
    expect(defaultEnd(-5)).toBe("30:00");
  });
});

describe("setTrimPoint", () => {
  it("keeps at least one second between the handles", () => {
    expect(setTrimPoint(10, 20, "start", 25, null)).toEqual({ start: 19, end: 20 });
    expect(setTrimPoint(10, 20, "end", 5, null)).toEqual({ start: 10, end: 11 });
  });

  it("does not move a handle past the video", () => {
    expect(setTrimPoint(10, 40, "start", 100, 30)).toEqual({ start: 29, end: 40 });
    expect(setTrimPoint(10, 20, "end", 100, 30)).toEqual({ start: 10, end: 30 });
    expect(setTrimPoint(10, 20, "start", -5, null)).toEqual({ start: 0, end: 20 });
  });
});
