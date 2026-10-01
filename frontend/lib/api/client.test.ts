// @vitest-environment jsdom
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { TooManyAttemptsError, UnauthorizedError, rememberPassword } from "./auth";
import { request } from "./client";

function jsonResponse(status: number, body: unknown): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

describe("request", () => {
  const fetchMock = vi.fn<typeof fetch>();

  beforeEach(() => {
    vi.stubGlobal("fetch", fetchMock);
    localStorage.clear();
  });

  afterEach(() => {
    fetchMock.mockReset();
    vi.unstubAllGlobals();
  });

  it("returns the JSON body and sends JSON headers", async () => {
    fetchMock.mockResolvedValue(jsonResponse(200, { ok: true }));

    await expect(request("/api/session", { headers: { "X-Extra": "1" } })).resolves.toEqual({
      ok: true,
    });

    const [url, init] = fetchMock.mock.calls[0] ?? [];
    expect(url).toBe("/api/session");
    expect(init?.headers).toEqual({ "Content-Type": "application/json", "X-Extra": "1" });
  });

  it("sends the remembered password as a bearer token", async () => {
    rememberPassword("synthetic-test-password");
    fetchMock.mockResolvedValue(jsonResponse(200, {}));

    await request("/api/logs");

    const init = fetchMock.mock.calls[0]?.[1];
    expect(init?.headers).toMatchObject({ Authorization: "Bearer synthetic-test-password" });
  });

  it("explains a network failure", async () => {
    fetchMock.mockRejectedValue(new TypeError("Failed to fetch"));
    await expect(request("/api/logs")).rejects.toThrow("Could not reach the API");
  });

  it("passes other errors through and wraps non-errors", async () => {
    const aborted = new Error("aborted");
    fetchMock.mockRejectedValueOnce(aborted);
    await expect(request("/api/logs")).rejects.toBe(aborted);

    fetchMock.mockRejectedValueOnce("weird");
    await expect(request("/api/logs")).rejects.toThrow("Could not reach the API");
  });

  it("raises UnauthorizedError on 401 with the server's sentence", async () => {
    fetchMock.mockResolvedValue(jsonResponse(401, { detail: "Wrong password." }));
    const result = request("/api/logs");
    await expect(result).rejects.toBeInstanceOf(UnauthorizedError);
    await expect(result).rejects.toThrow("Wrong password.");
  });

  it("raises TooManyAttemptsError on 429", async () => {
    fetchMock.mockResolvedValue(jsonResponse(429, { detail: "Slow down." }));
    await expect(request("/api/logs")).rejects.toBeInstanceOf(TooManyAttemptsError);
  });

  it("uses the detail string from an error response", async () => {
    fetchMock.mockResolvedValue(jsonResponse(400, { detail: "Clip 1 ends before it starts." }));
    await expect(request("/api/compilations")).rejects.toThrow("Clip 1 ends before it starts.");
  });

  it("stringifies structured validation details", async () => {
    const detail = [{ loc: ["body", "url"], msg: "Field required" }];
    fetchMock.mockResolvedValue(jsonResponse(422, { detail }));
    await expect(request("/api/channels")).rejects.toThrow(JSON.stringify(detail));
  });

  it("falls back to the status when there is no usable detail", async () => {
    fetchMock.mockResolvedValueOnce(jsonResponse(500, {}));
    await expect(request("/api/logs")).rejects.toThrow("Request failed with status 500");

    fetchMock.mockResolvedValueOnce(jsonResponse(500, { detail: null }));
    await expect(request("/api/logs")).rejects.toThrow("Request failed with status 500");

    fetchMock.mockResolvedValueOnce(jsonResponse(503, "not an object"));
    await expect(request("/api/logs")).rejects.toThrow("Request failed with status 503");
  });

  it("treats a non-JSON body as empty", async () => {
    fetchMock.mockResolvedValueOnce(new Response("<html>Bad gateway</html>", { status: 502 }));
    await expect(request("/api/logs")).rejects.toThrow("Request failed with status 502");

    fetchMock.mockResolvedValueOnce(new Response("", { status: 200 }));
    await expect(request("/api/logs")).resolves.toBeNull();
  });

  it("reports a body that cannot be read", async () => {
    const broken = new Response("{}", { status: 200 });
    vi.spyOn(broken, "json").mockRejectedValue("stream closed");
    fetchMock.mockResolvedValue(broken);
    await expect(request("/api/logs")).rejects.toThrow("Could not read the API response.");
  });
});

describe("API_BASE", () => {
  afterEach(() => {
    vi.unstubAllEnvs();
    vi.unstubAllGlobals();
    vi.resetModules();
  });

  it("trims trailing slashes and names the base in network errors", async () => {
    vi.stubEnv("NEXT_PUBLIC_API_URL", " https://api.example.test// ");
    vi.resetModules();
    const fetchMock = vi.fn<typeof fetch>().mockRejectedValue(new TypeError("offline"));
    vi.stubGlobal("fetch", fetchMock);
    const client = await import("./client");

    expect(client.API_BASE).toBe("https://api.example.test");
    await expect(client.request("/api/logs")).rejects.toThrow(
      "Could not reach the API at https://api.example.test",
    );
    expect(fetchMock.mock.calls[0]?.[0]).toBe("https://api.example.test/api/logs");
  });
});
