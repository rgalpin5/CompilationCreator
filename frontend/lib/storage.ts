// Browser storage can be missing or throw: private windows, blocked site
// data, or a server render. These helpers treat every failure as "nothing
// stored" so a remembered preference never breaks the page.

type StringStorage = Pick<Storage, "getItem" | "setItem">;

function browserStorage(): StringStorage | null {
  try {
    return typeof window === "undefined" ? null : window.localStorage;
  } catch {
    return null;
  }
}

/** The stored string for ``key``, or ``null`` when storage is unavailable. */
export function readStored(key: string, storage = browserStorage()): string | null {
  if (!storage) return null;
  try {
    return storage.getItem(key);
  } catch {
    return null;
  }
}

/** Remember ``value`` under ``key``. Returns ``false`` when storage refused it. */
export function writeStored(key: string, value: string, storage = browserStorage()): boolean {
  if (!storage) return false;
  try {
    storage.setItem(key, value);
    return true;
  } catch {
    return false;
  }
}
