/**
 * Which build this is. The desktop app is a personal, already-licensed copy, so
 * it opens straight into the studio with no landing page, account or purchase.
 */
export const isDesktopEdition = process.env.NEXT_PUBLIC_EDITION === "desktop";
