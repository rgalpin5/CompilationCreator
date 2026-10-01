import { request } from "./client";
import type { Logs, UsageCounts } from "./types";

/** Videos and compilations recorded on this computer. */
export function fetchLogs(): Promise<Logs> {
  return request<Logs>("/api/logs");
}

/** Compilation counts for ``ids``. An empty list does not call the API. */
export async function fetchUsage(ids: string[]): Promise<Record<string, number>> {
  if (ids.length === 0) return {};
  const data = await request<UsageCounts>(
    `/api/usage?ids=${ids.map((id) => encodeURIComponent(id)).join(",")}`,
  );
  return data.counts;
}
