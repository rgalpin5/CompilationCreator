import type { ReactNode } from "react";

/** A timeline marker: a flag, a timecode and a hairline that runs off the page. */
export default function Marker({ timecode, children }: { timecode: string; children: ReactNode }) {
  return (
    <div className="flex items-center gap-3 font-mono text-2xs tracking-widest text-muted-foreground uppercase">
      <span
        aria-hidden="true"
        className="h-3.5 w-2.5 bg-primary [clip-path:polygon(0_0,100%_0,100%_60%,50%_100%,0_60%)]"
      />
      <span aria-hidden="true" className="text-primary tabular-nums">{timecode}</span>
      <span>{children}</span>
      <span aria-hidden="true" className="h-px flex-1 bg-border" />
    </div>
  );
}
