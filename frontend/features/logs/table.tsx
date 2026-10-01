"use client";

import type { ReactNode } from "react";

/** Shared scrollable table used by the two log views. */
export function LogTable({
  children,
  empty,
  isEmpty,
}: {
  children: ReactNode;
  empty: string;
  isEmpty: boolean;
}) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full min-w-[720px] border-collapse text-sm">{children}</table>
      {isEmpty && <p className="px-2 py-6 text-sm text-muted-foreground">{empty}</p>}
    </div>
  );
}

/** A column header that toggles its sort direction. */
export function SortButton({
  active,
  onClick,
  children,
}: {
  active: boolean;
  onClick: () => void;
  children: ReactNode;
}) {
  return (
    <button type="button" onClick={onClick} className="uppercase">
      {children}
      {active ? <span aria-hidden="true"> •</span> : null}
    </button>
  );
}
