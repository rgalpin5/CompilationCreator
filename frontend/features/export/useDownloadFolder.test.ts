// @vitest-environment jsdom
import { act, renderHook, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { fetchDownloadFolder } from "@/lib/api/compilations";
import { useDownloadFolder } from "./useDownloadFolder";

vi.mock("@/lib/api/compilations", () => ({ fetchDownloadFolder: vi.fn() }));

const fetchFolder = vi.mocked(fetchDownloadFolder);
const KEY = "compcreator-download-folder";

describe("useDownloadFolder", () => {
  beforeEach(() => {
    localStorage.clear();
  });

  afterEach(() => {
    fetchFolder.mockReset();
  });

  it("restores the remembered folder without asking the server", async () => {
    localStorage.setItem(KEY, "/Users/me/Movies");
    const hook = renderHook(() => useDownloadFolder());
    await waitFor(() => expect(hook.result.current.folder).toBe("/Users/me/Movies"));
    expect(fetchFolder).not.toHaveBeenCalled();
  });

  it("falls back to the server's default folder", async () => {
    fetchFolder.mockResolvedValue("/Users/me/Downloads");
    const hook = renderHook(() => useDownloadFolder());
    await waitFor(() => expect(hook.result.current.folder).toBe("/Users/me/Downloads"));
  });

  it("keeps a folder typed before the server answered", async () => {
    let answer!: (path: string) => void;
    fetchFolder.mockReturnValue(new Promise((resolve) => (answer = resolve)));
    const hook = renderHook(() => useDownloadFolder());

    act(() => hook.result.current.changeFolder("/typed"));
    await act(async () => answer("/Users/me/Downloads"));

    expect(hook.result.current.folder).toBe("/typed");
  });

  it("stays blank when the server request fails", async () => {
    fetchFolder.mockRejectedValue(new Error("offline"));
    const hook = renderHook(() => useDownloadFolder());
    await act(async () => {});
    expect(hook.result.current.folder).toBe("");
  });

  it("remembers a changed folder", () => {
    fetchFolder.mockResolvedValue("");
    const hook = renderHook(() => useDownloadFolder());
    act(() => hook.result.current.changeFolder("/Volumes/Edits"));
    expect(hook.result.current.folder).toBe("/Volumes/Edits");
    expect(localStorage.getItem(KEY)).toBe("/Volumes/Edits");
  });
});
