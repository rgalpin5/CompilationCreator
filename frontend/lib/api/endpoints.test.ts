import { afterEach, describe, expect, it, vi } from "vitest";
import { fetchChannelVideos } from "./channels";
import { request } from "./client";
import {
  cancelCompilation,
  compilationFileHref,
  createCompilation,
  fetchDownloadFolder,
  getCompilation,
  saveCompilation,
} from "./compilations";
import { checkSession } from "./session";
import { fetchLogs, fetchUsage } from "./usage";

vi.mock("./client", () => ({ API_BASE: "", request: vi.fn() }));

const requestMock = vi.mocked(request);

function lastCall(): [string, RequestInit | undefined] {
  const call = requestMock.mock.calls.at(-1);
  if (!call) throw new Error("request was not called");
  return [call[0], call[1]];
}

describe("API endpoint wrappers", () => {
  afterEach(() => {
    requestMock.mockReset();
  });

  it("posts the channel URL with paging in the query", async () => {
    requestMock.mockResolvedValue({ videos: [], has_more: false, next_offset: 0 });
    await fetchChannelVideos("https://www.youtube.com/@x", 12, 24);
    const [path, init] = lastCall();
    expect(path).toBe("/api/channels?limit=12&offset=24");
    expect(init?.method).toBe("POST");
    expect(JSON.parse(String(init?.body))).toEqual({ url: "https://www.youtube.com/@x" });
  });

  it("uses the default page size", async () => {
    requestMock.mockResolvedValue({ videos: [], has_more: false, next_offset: 0 });
    await fetchChannelVideos("https://www.youtube.com/@x");
    expect(lastCall()[0]).toBe("/api/channels?limit=24&offset=0");
  });

  it("creates a compilation with the 4K flag", async () => {
    requestMock.mockResolvedValue({ id: "job" });
    const clips = [
      { video_id: "dQw4w9WgXcQ", title: "Intro", start: "0:01", end: "0:05", order: 0 },
    ];
    await createCompilation(clips, true);
    const [path, init] = lastCall();
    expect(path).toBe("/api/compilations");
    expect(JSON.parse(String(init?.body))).toEqual({ clips, output_4k: true });

    await createCompilation(clips);
    expect(JSON.parse(String(lastCall()[1]?.body)).output_4k).toBe(false);
  });

  it("encodes job ids in status, cancel and save paths", async () => {
    requestMock.mockResolvedValue({});
    await getCompilation("a/b");
    expect(lastCall()[0]).toBe("/api/compilations/a%2Fb");

    await cancelCompilation("a/b");
    expect(lastCall()).toEqual(["/api/compilations/a%2Fb/cancel", { method: "POST" }]);

    await saveCompilation("a/b", "  /Users/me/Movies ");
    const [path, init] = lastCall();
    expect(path).toBe("/api/compilations/a%2Fb/download");
    expect(JSON.parse(String(init?.body))).toEqual({ directory: "/Users/me/Movies" });
  });

  it("sends null for a blank save folder", async () => {
    requestMock.mockResolvedValue({});
    await saveCompilation("job", "   ");
    expect(JSON.parse(String(lastCall()[1]?.body))).toEqual({ directory: null });
  });

  it("reads the default download folder path", async () => {
    requestMock.mockResolvedValue({ path: "/Users/me/Downloads" });
    await expect(fetchDownloadFolder()).resolves.toBe("/Users/me/Downloads");
    expect(lastCall()[0]).toBe("/api/download-folder");
  });

  it("builds file links from the API base", () => {
    expect(compilationFileHref("/api/compilations/job/file?token=t")).toBe(
      "/api/compilations/job/file?token=t",
    );
  });

  it("reads logs and checks the session", async () => {
    requestMock.mockResolvedValue({ ok: true });
    await fetchLogs();
    expect(lastCall()[0]).toBe("/api/logs");
    await expect(checkSession()).resolves.toBeUndefined();
    expect(lastCall()[0]).toBe("/api/session");
  });

  it("fetches usage counts for encoded ids", async () => {
    requestMock.mockResolvedValue({ counts: { a: 2 } });
    await expect(fetchUsage(["a", "b c"])).resolves.toEqual({ a: 2 });
    expect(lastCall()[0]).toBe("/api/usage?ids=a,b%20c");
  });

  it("skips the usage request for no ids", async () => {
    await expect(fetchUsage([])).resolves.toEqual({});
    expect(requestMock).not.toHaveBeenCalled();
  });
});
