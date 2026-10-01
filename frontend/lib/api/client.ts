import { UnauthorizedError, authHeaders, storedPassword } from "./auth";

// Same origin by default, as in the desktop app, where one process serves the
// UI and the API. Set NEXT_PUBLIC_API_URL when the API is on another origin:
// the Cloud Run URL for the Vercel UI, or uvicorn on port 8000 during
// `npm run dev`. Every call below runs in the browser.
const configured = process.env.NEXT_PUBLIC_API_URL?.trim().replace(/\/+$/, "");
export const API_BASE = configured ? configured : "";

/**
 * Call one API path and return the JSON body as ``T``.
 *
 * Network failures and HTTP errors become ``Error`` messages a person can read.
 * The caller supplies ``T``; this function does not validate the JSON shape.
 */
export async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let res: Response;
  try {
    res = await fetch(`${API_BASE}${path}`, {
      ...init,
      headers: {
        "Content-Type": "application/json",
        ...authHeaders(storedPassword()),
        ...init?.headers,
      },
    });
  } catch (caught: unknown) {
    if (caught instanceof TypeError) {
      throw new Error(
        API_BASE ? `Could not reach the API at ${API_BASE}` : "Could not reach the API",
      );
    }
    throw caught instanceof Error ? caught : new Error("Could not reach the API");
  }

  const body = await readJson(res);
  if (res.status === 401) {
    throw new UnauthorizedError(detailMessage(body, res.status));
  }
  if (!res.ok) {
    throw new Error(detailMessage(body, res.status));
  }
  return body as T;
}

async function readJson(res: Response): Promise<unknown> {
  try {
    return await res.json();
  } catch (caught: unknown) {
    if (caught instanceof SyntaxError) return null;
    throw caught instanceof Error ? caught : new Error("Could not read the API response.");
  }
}

function detailMessage(body: unknown, status: number): string {
  if (body === null || typeof body !== "object" || !("detail" in body)) {
    return `Request failed with status ${status}`;
  }
  const detail: unknown = body.detail;
  if (typeof detail === "string" && detail.trim()) return detail;
  if (detail !== undefined && detail !== null) return JSON.stringify(detail);
  return `Request failed with status ${status}`;
}
