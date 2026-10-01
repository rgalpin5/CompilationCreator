// Browser storage can be missing or throw: private windows, blocked site
// data, or a server render. These helpers treat every failure as "nothing
// stored" so a remembered preference never breaks the page.

type StringStorage = Pick<Storage, "getItem" | "setItem">;

function browserStorage(): Storage | null {
  try {
    return typeof window === "undefined" ? null : window.localStorage;
  } catch {
    return null;
  }
}

/** This tab's storage, which the browser clears when the tab closes. */
export function tabStorage(): Storage | null {
  try {
    return typeof window === "undefined" ? null : window.sessionStorage;
  } catch {
    return null;
  }
}

/** The stored string for ``key``, or ``null`` when storage is unavailable. */
export function readStored(
  key: string,
  storage: StringStorage | null = browserStorage(),
): string | null {
  if (!storage) return null;
  try {
    return storage.getItem(key);
  } catch {
    return null;
  }
}

/** Remember ``value`` under ``key``. Returns ``false`` when storage refused it. */
export function writeStored(
  key: string,
  value: string,
  storage: StringStorage | null = browserStorage(),
): boolean {
  if (!storage) return false;
  try {
    storage.setItem(key, value);
    return true;
  } catch {
    return false;
  }
}

/** Forget ``key``. Storage that is missing or throws is left alone. */
export function removeStored(
  key: string,
  storage: Pick<Storage, "removeItem"> | null = browserStorage(),
): void {
  if (!storage) return;
  try {
    storage.removeItem(key);
  } catch {
    // Nothing was stored, or the browser blocks site data.
  }
}
