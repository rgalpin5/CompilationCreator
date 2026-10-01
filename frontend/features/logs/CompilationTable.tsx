"use client";

import { useMemo, useState } from "react";
import type { CompilationLog } from "@/lib/api/types";
import { formatSeconds } from "@/lib/time";
import { Input } from "@/components/ui/input";
import { formatWhen } from "./format";
import { LogTable, SortButton } from "./table";

type Props = {
  compilations: CompilationLog[];
};

/** Searchable table of finished compilations. */
export default function CompilationTable({ compilations }: Props) {
  const [compilationQuery, setCompilationQuery] = useState("");
  const [compilationSort, setCompilationSort] = useState<"newest" | "oldest">("newest");

  const shownCompilations = useMemo(() => {
    const query = compilationQuery.trim().toLowerCase();
    const filtered = compilations.filter((item) =>
      query ? item.name.toLowerCase().includes(query) : true,
    );
    return filtered.sort((a, b) =>
      compilationSort === "newest" ? b.made.localeCompare(a.made) : a.made.localeCompare(b.made),
    );
  }, [compilations, compilationQuery, compilationSort]);

  return (
    <section className="flex flex-col gap-3">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h2 className="flex items-center gap-2 text-base font-medium">
          Compilations
          <span className="rounded-full bg-muted px-2 py-0.5 text-xs text-muted-foreground">
            {compilations.length}
          </span>
        </h2>
        <Input
          value={compilationQuery}
          onChange={(event) => setCompilationQuery(event.target.value)}
          placeholder="Search compilations"
          aria-label="Search compilations"
          className="w-full sm:max-w-56"
        />
      </div>
      <LogTable
        empty={
          compilations.length === 0
            ? "Finished compilations are listed here."
            : "No compilations match that search."
        }
        isEmpty={shownCompilations.length === 0}
      >
        <thead>
          <tr className="text-left text-xs tracking-wide text-muted-foreground uppercase">
            <th className="px-2 py-2 font-medium">Name</th>
            <th
              className="px-2 py-2 font-medium"
              aria-sort={compilationSort === "newest" ? "descending" : "ascending"}
            >
              <SortButton
                active
                onClick={() =>
                  setCompilationSort((current) => (current === "newest" ? "oldest" : "newest"))
                }
              >
                Made
              </SortButton>
            </th>
            <th className="px-2 py-2 font-medium">Clips</th>
            <th className="px-2 py-2 font-medium">Length</th>
          </tr>
        </thead>
        <tbody>
          {shownCompilations.map((item) => (
            <tr key={`${item.name}-${item.made}`} className="border-t border-border">
              <td className="px-2 py-3">{item.name}</td>
              <td className="px-2 py-3 text-muted-foreground">{formatWhen(item.made)}</td>
              <td className="px-2 py-3 text-muted-foreground">{item.clips}</td>
              <td className="px-2 py-3 text-muted-foreground">
                {formatSeconds(item.duration_seconds)}
              </td>
            </tr>
          ))}
        </tbody>
      </LogTable>
    </section>
  );
}
