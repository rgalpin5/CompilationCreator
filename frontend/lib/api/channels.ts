import { request } from "./client";
import type { ChannelPage } from "./types";

/** Load one page of videos for a channel URL. */
export async function fetchChannelVideos(
  url: string,
  limit = 24,
  offset = 0,
): Promise<ChannelPage> {
  return request<ChannelPage>(`/api/channels?limit=${limit}&offset=${offset}`, {
    method: "POST",
    body: JSON.stringify({ url }),
  });
}
