import { readStored, writeStored } from "../storage";

const PASSWORD_KEY = "compcreator-password";

/** Thrown when the API answers 401: its password is missing or wrong. */
export class UnauthorizedError extends Error {
  constructor(message = "This server needs its password.") {
    super(message);
    this.name = "UnauthorizedError";
  }
}

/** Thrown when the API answers 429: this browser sent too many wrong passwords. */
export class TooManyAttemptsError extends Error {
  constructor(message = "Too many wrong passwords. Try again later.") {
    super(message);
    this.name = "TooManyAttemptsError";
  }
}

/** The password remembered in this browser for a hosted API, if any. */
export function storedPassword(): string | null {
  return readStored(PASSWORD_KEY);
}

/** Remember ``password`` in this browser so later requests send it. */
export function rememberPassword(password: string): void {
  writeStored(PASSWORD_KEY, password);
}

/** The header a hosted API expects. Empty when no password is known. */
export function authHeaders(password: string | null): Record<string, string> {
  const value = password?.trim();
  return value ? { Authorization: `Bearer ${value}` } : {};
}
