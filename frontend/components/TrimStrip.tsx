import { cn } from "@/lib/utils";

type Props = {
  /** Full length of the source video, in seconds. */
  duration: number;
  /** Kept range, in seconds. */
  start: number;
  end: number;
  className?: string;
};

/** One clip at a glance: hatched cut ends around the kept span. */
export default function TrimStrip({ duration, start, end, className }: Props) {
  const safe = duration > 0 ? duration : 1;
  const left = Math.min(100, Math.max(0, (start / safe) * 100));
  const right = Math.min(100, Math.max(left, (end / safe) * 100));
  return (
    <div
      aria-hidden="true"
      className={cn("relative h-1.5 w-full overflow-hidden rounded-full bg-hatch-cut", className)}
    >
      <div
        className="absolute inset-y-0 rounded-full bg-keep"
        style={{ left: `${left}%`, width: `${right - left}%` }}
      />
    </div>
  );
}
