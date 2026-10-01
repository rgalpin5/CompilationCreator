import { describe, expect, it } from "vitest";
import { TooManyAttemptsError, UnauthorizedError, authHeaders } from "./auth";

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

describe("TooManyAttemptsError", () => {
  it("is an Error that keeps the server's message", () => {
    const error = new TooManyAttemptsError("Too many wrong passwords. Try again in 15 minutes.");
    expect(error).toBeInstanceOf(Error);
    expect(error).not.toBeInstanceOf(UnauthorizedError);
    expect(error.message).toBe("Too many wrong passwords. Try again in 15 minutes.");
  });
});
