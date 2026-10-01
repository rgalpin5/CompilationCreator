import { request } from "./client";
import type { Ok } from "./types";

/** Resolve when this browser may use the API. Rejects with ``UnauthorizedError`` otherwise. */
export async function checkSession(): Promise<void> {
  await request<Ok>("/api/session");
}
