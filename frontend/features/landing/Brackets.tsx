import { cn } from "@/lib/utils";

const CORNERS = [
  "top-0 left-0 border-t-2 border-l-2",
  "top-0 right-0 border-t-2 border-r-2",
  "bottom-0 left-0 border-b-2 border-l-2",
  "bottom-0 right-0 border-b-2 border-r-2",
];

/** Viewfinder corner marks, drawn just outside the parent's edge. */
export default function Brackets({ className }: { className?: string }) {
  return (
    <span aria-hidden="true" className="pointer-events-none absolute -inset-2">
      {CORNERS.map((corner) => (
        <span key={corner} className={cn("absolute size-3.5", corner, className)} />
      ))}
    </span>
  );
}
