import { describe, expect, it } from "vitest";

import { formatViews, formatWhen } from "./format";

describe("formatViews", () => {
  it("uses an em dash when the count is unknown", () => {
    expect(formatViews(null)).toBe("—");
  });

  it("keeps small counts and rounds thousands and millions", () => {
    expect(formatViews(0)).toBe("0");
    expect(formatViews(999)).toBe("999");
    expect(formatViews(1500)).toBe("2K");
    expect(formatViews(1_000_000)).toBe("1M");
    expect(formatViews(1_500_000)).toBe("1.5M");
    expect(formatViews(10_000_000)).toBe("10M");
  });
});

describe("formatWhen", () => {
  it("uses an em dash when the time is missing or invalid", () => {
    expect(formatWhen(null)).toBe("—");
    expect(formatWhen("")).toBe("—");
    expect(formatWhen("not-a-date")).toBe("—");
  });

  it("formats the local date and time", () => {
    const date = new Date(2026, 8, 29, 17, 4, 0);
    expect(formatWhen(date.toISOString())).toBe("29 Sep, 17:04");
  });
});
