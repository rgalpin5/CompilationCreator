import { describe, expect, it } from "vitest";
import { readStored, removeStored, writeStored } from "./storage";

function memoryStorage(): Pick<Storage, "getItem" | "setItem"> {
  const values = new Map<string, string>();
  return {
    getItem: (key) => values.get(key) ?? null,
    setItem: (key, value) => {
      values.set(key, value);
    },
  };
}

const blocked: Pick<Storage, "getItem" | "setItem"> = {
  getItem: () => {
    throw new DOMException("blocked", "SecurityError");
  },
  setItem: () => {
    throw new DOMException("full", "QuotaExceededError");
  },
};

describe("readStored and writeStored", () => {
  it("round-trips a value", () => {
    const storage = memoryStorage();
    expect(writeStored("folder", "/Users/me/Downloads", storage)).toBe(true);
    expect(readStored("folder", storage)).toBe("/Users/me/Downloads");
  });

  it("treats storage that throws as empty", () => {
    expect(readStored("folder", blocked)).toBeNull();
    expect(writeStored("folder", "/tmp", blocked)).toBe(false);
  });

  it("treats missing storage as empty", () => {
    expect(readStored("folder", null)).toBeNull();
    expect(writeStored("folder", "/tmp", null)).toBe(false);
  });
});

describe("removeStored", () => {
  it("forgets a stored value", () => {
    const values = new Map([["folder", "/tmp"]]);
    removeStored("folder", { removeItem: (key) => values.delete(key) });
    expect(values.has("folder")).toBe(false);
  });

  it("ignores storage that throws or is missing", () => {
    const throwing = {
      removeItem: () => {
        throw new DOMException("blocked", "SecurityError");
      },
    };
    expect(() => removeStored("folder", throwing)).not.toThrow();
    expect(() => removeStored("folder", null)).not.toThrow();
  });
});
