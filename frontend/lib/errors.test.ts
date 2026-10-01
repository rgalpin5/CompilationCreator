import { describe, expect, it } from "vitest";

import { errorMessage } from "./errors";

describe("errorMessage", () => {
  it("returns a trimmed error or string", () => {
    expect(errorMessage(new Error("  boom  "))).toBe("boom");
    expect(errorMessage("  hi  ")).toBe("hi");
  });

  it("uses a generic sentence when nothing usable was thrown", () => {
    expect(errorMessage(new Error("   "))).toBe("Something went wrong. Try again.");
    expect(errorMessage("")).toBe("Something went wrong. Try again.");
    expect(errorMessage(12)).toBe("Something went wrong. Try again.");
    expect(errorMessage(null)).toBe("Something went wrong. Try again.");
  });
});
