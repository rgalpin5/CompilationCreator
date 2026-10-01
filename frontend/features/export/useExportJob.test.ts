// @vitest-environment jsdom
import { act, renderHook } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import type { TimelineClip } from "@/features/timeline/types";
import {
  cancelCompilation,
  createCompilation,
  getCompilation,
  saveCompilation,
} from "@/lib/api/compilations";
import type { Job } from "@/lib/api/types";
import { useExportJob } from "./useExportJob";

vi.mock("@/lib/api/compilations", () => ({
  cancelCompilation: vi.fn(),
  createCompilation: vi.fn(),
  getCompilation: vi.fn(),
  saveCompilation: vi.fn(),
}));

const POLL_MS = 2000;
const CLIP: TimelineClip = { video_id: "dQw4w9WgXcQ", title: "Intro", start: "00:01", end: "00:05" };
const CLIPS = [CLIP];

function job(patch: Partial<Job> = {}): Job {
  return {
    id: "job-1",
    status: "queued",
    progress: "Queued",
    error: null,
    download_url: null,
    file_url: null,
    saved_path: null,
    ...patch,
  };
}

function setup(clips: TimelineClip[] = CLIPS) {
  const refreshUsage = vi.fn(async () => {});
  const onExported = vi.fn();
  const setValidationError = vi.fn();
  const hook = renderHook(() =>
    useExportJob({ clips, output4k: false, setValidationError, refreshUsage, onExported }),
  );
  return { hook, refreshUsage, onExported, setValidationError };
}

async function startExport(hook: ReturnType<typeof setup>["hook"]): Promise<void> {
  await act(async () => {
    await hook.result.current.exportCompilation();
  });
}

async function tick(): Promise<void> {
  await act(async () => {
    await vi.advanceTimersByTimeAsync(POLL_MS);
  });
}

describe("useExportJob polling", () => {
  beforeEach(() => {
    vi.useFakeTimers();
    vi.mocked(createCompilation).mockResolvedValue(job());
  });

  afterEach(() => {
    vi.useRealTimers();
    vi.resetAllMocks();
  });

  it("polls every two seconds until the job is ready, then refreshes usage", async () => {
    vi.mocked(getCompilation)
      .mockResolvedValueOnce(job({ status: "downloading", progress: "Downloading" }))
      .mockResolvedValueOnce(job({ status: "ready", progress: "Ready" }));
    const { hook, refreshUsage, onExported } = setup();

    await startExport(hook);
    expect(onExported).toHaveBeenCalledOnce();
    expect(hook.result.current.jobActive).toBe(true);
    expect(getCompilation).not.toHaveBeenCalled();

    await tick();
    expect(getCompilation).toHaveBeenCalledTimes(1);
    expect(hook.result.current.job?.status).toBe("downloading");

    await tick();
    expect(hook.result.current.job?.status).toBe("ready");
    expect(hook.result.current.jobActive).toBe(false);
    expect(refreshUsage).toHaveBeenCalledOnce();

    await tick();
    expect(getCompilation).toHaveBeenCalledTimes(2);
  });

  it("keeps polling through a dropped request", async () => {
    vi.mocked(getCompilation)
      .mockRejectedValueOnce(new Error("offline"))
      .mockResolvedValueOnce(job({ status: "concatenating", progress: "Joining clips" }));
    const { hook } = setup();

    await startExport(hook);
    await tick();
    expect(hook.result.current.job?.status).toBe("queued");
    expect(hook.result.current.requestError).toBeNull();

    await tick();
    expect(hook.result.current.job?.status).toBe("concatenating");
  });

  it("reports the job lost after three failed requests in a row", async () => {
    vi.mocked(getCompilation).mockRejectedValue(new Error("Network down"));
    const { hook } = setup();

    await startExport(hook);
    await tick();
    await tick();
    expect(hook.result.current.jobActive).toBe(true);

    await tick();
    expect(hook.result.current.job?.status).toBe("failed");
    expect(hook.result.current.job?.error).toBe("Lost track of the job.");
    expect(hook.result.current.requestError).toBe("Network down");

    await tick();
    expect(getCompilation).toHaveBeenCalledTimes(3);
  });

  it("resets the failure count after a successful request", async () => {
    vi.mocked(getCompilation)
      .mockRejectedValueOnce(new Error("offline"))
      .mockRejectedValueOnce(new Error("offline"))
      .mockResolvedValueOnce(job({ status: "downloading", progress: "Downloading" }))
      .mockRejectedValueOnce(new Error("offline"))
      .mockRejectedValueOnce(new Error("offline"))
      .mockResolvedValueOnce(job({ status: "ready", progress: "Ready" }));
    const { hook } = setup();

    await startExport(hook);
    for (let i = 0; i < 5; i += 1) await tick();
    expect(hook.result.current.job?.status).toBe("downloading");

    await tick();
    expect(hook.result.current.job?.status).toBe("ready");
  });

  it("stops polling once the export is cancelled", async () => {
    vi.mocked(cancelCompilation).mockResolvedValue(
      job({ status: "cancelled", progress: "Cancelled" }),
    );
    const { hook } = setup();

    await startExport(hook);
    await act(async () => {
      await hook.result.current.cancelExport();
    });
    expect(hook.result.current.job?.status).toBe("cancelled");

    await tick();
    expect(getCompilation).not.toHaveBeenCalled();
  });

  it("does not start an export when the timeline is invalid", async () => {
    const { hook, setValidationError } = setup([{ ...CLIP, end: "00:00" }]);

    await startExport(hook);
    expect(setValidationError).toHaveBeenLastCalledWith(expect.any(String));
    expect(createCompilation).not.toHaveBeenCalled();
  });
});

describe("useExportJob requests", () => {
  afterEach(() => {
    vi.mocked(createCompilation).mockReset();
    vi.mocked(cancelCompilation).mockReset();
    vi.mocked(saveCompilation).mockReset();
    vi.mocked(getCompilation).mockReset();
  });

  it("sends trimmed clips in timeline order", async () => {
    vi.mocked(createCompilation).mockResolvedValue(job({ status: "ready" }));
    const second = { ...CLIP, video_id: "abcdefghijk", start: " 00:02 ", end: "00:09 " };
    const { hook, onExported } = setup([CLIP, second]);

    await startExport(hook);

    const [clips, output4k] = vi.mocked(createCompilation).mock.calls[0] ?? [];
    expect(output4k).toBe(false);
    expect(clips?.map((c) => [c.video_id, c.start, c.end, c.order])).toEqual([
      ["dQw4w9WgXcQ", "00:01", "00:05", 0],
      ["abcdefghijk", "00:02", "00:09", 1],
    ]);
    expect(onExported).toHaveBeenCalledTimes(1);
    expect(hook.result.current.submitting).toBe(false);
  });

  it("shows a create failure and clears it on request", async () => {
    vi.mocked(createCompilation).mockRejectedValue(new Error("Another export is running."));
    const { hook, onExported } = setup();

    await startExport(hook);

    expect(hook.result.current.requestError).toBe("Another export is running.");
    expect(hook.result.current.job).toBeNull();
    expect(onExported).not.toHaveBeenCalled();

    act(() => hook.result.current.clearRequestError());
    expect(hook.result.current.requestError).toBeNull();
  });

  it("does nothing on cancel or save without a job", async () => {
    const { hook } = setup();
    await act(async () => {
      await hook.result.current.cancelExport();
      await hook.result.current.downloadExport("/tmp");
    });
    expect(cancelCompilation).not.toHaveBeenCalled();
    expect(saveCompilation).not.toHaveBeenCalled();
  });

  it("shows a cancel failure", async () => {
    vi.mocked(createCompilation).mockResolvedValue(job({ status: "ready" }));
    vi.mocked(cancelCompilation).mockRejectedValue(new Error("Job not found"));
    const { hook } = setup();
    await startExport(hook);

    await act(async () => {
      await hook.result.current.cancelExport();
    });

    expect(hook.result.current.requestError).toBe("Job not found");
  });

  it("saves a finished export into the chosen folder", async () => {
    vi.mocked(createCompilation).mockResolvedValue(job({ status: "ready" }));
    vi.mocked(saveCompilation).mockResolvedValue(
      job({ status: "saved", saved_path: "/Users/me/Movies/out.mp4" }),
    );
    const { hook } = setup();
    await startExport(hook);

    await act(async () => {
      await hook.result.current.downloadExport("/Users/me/Movies");
    });

    expect(saveCompilation).toHaveBeenCalledWith("job-1", "/Users/me/Movies");
    expect(hook.result.current.job?.status).toBe("saved");
    expect(hook.result.current.savingDownload).toBe(false);
  });

  it("shows a save failure and allows another try", async () => {
    vi.mocked(createCompilation).mockResolvedValue(job({ status: "ready" }));
    vi.mocked(saveCompilation).mockRejectedValue(new Error("Permission denied for /x."));
    const { hook } = setup();
    await startExport(hook);

    await act(async () => {
      await hook.result.current.downloadExport("/x");
    });

    expect(hook.result.current.requestError).toBe("Permission denied for /x.");
    expect(hook.result.current.savingDownload).toBe(false);
    expect(hook.result.current.job?.status).toBe("ready");
  });
});
