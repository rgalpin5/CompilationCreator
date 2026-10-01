import { request } from "./client";

/** Resolve when this browser may use the API. Rejects with ``UnauthorizedError`` otherwise. */
export async function checkSession(): Promise<void> {
  await request<{ ok: boolean }>("/api/session");
}
