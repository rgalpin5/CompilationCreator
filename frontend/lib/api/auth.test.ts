import { describe, expect, it } from "vitest";
import { UnauthorizedError, authHeaders } from "./auth";

describe("authHeaders", () => {
  it("sends a bearer header when a password is known", () => {
    expect(authHeaders("synthetic-test-password")).toEqual({
      Authorization: "Bearer synthetic-test-password",
    });
  });

  it("sends nothing without a password", () => {
    expect(authHeaders(null)).toEqual({});
    expect(authHeaders("   ")).toEqual({});
  });
});

describe("UnauthorizedError", () => {
  it("is an Error with a readable message", () => {
    const error = new UnauthorizedError();
    expect(error).toBeInstanceOf(Error);
    expect(error.message).toBe("This server needs its password.");
  });
});
