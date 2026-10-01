import { cn } from "@/lib/utils";

// Relative widths and trimmed ends of the clips in the illustration.
const CLIPS = [
  { grow: 5, intro: 14, outro: 10, label: "Opening goals" },
  { grow: 3, intro: 22, outro: 8, label: "Rally #12" },
  { grow: 6, intro: 9, outro: 16, label: "Finals recap" },
  { grow: 2, intro: 18, outro: 12, label: "Bloopers" },
  { grow: 4, intro: 12, outro: 20, label: "Top 10" },
];

// Fixed bar heights so the waveform renders the same on server and client.
const WAVE = [4, 7, 5, 9, 6, 3, 8, 10, 6, 4, 7, 9, 5, 3, 6, 8, 4, 7, 10, 5, 6, 9, 4, 3, 7, 8, 5, 6, 9, 4];

/** A stylised editing timeline: five clips with their intros and outros cut. */
export default function HeroReel() {
  return (
    <div className="relative overflow-hidden rounded-xl bg-card shadow-2xl shadow-black/40 ring-1 ring-border">
      <div className="flex items-center justify-between gap-3 border-b px-4 py-2.5 font-mono text-[11px] text-muted-foreground">
        <span className="truncate">compilation.mp4</span>
        <span className="flex shrink-0 items-center gap-3 tabular-nums">
          <span>5 clips</span>
          <span className="text-primary">00:42:18</span>
        </span>
      </div>

      <div className="relative flex flex-col gap-2 p-4">
        <Track label="V1">
          {CLIPS.map((clip) => (
            <div
              key={clip.label}
              className="flex h-14 min-w-0 overflow-hidden rounded-md ring-1 ring-black/30"
              style={{ flexGrow: clip.grow, flexBasis: 0 }}
            >
              <div className="bg-hatch-cut" style={{ width: `${clip.intro}%` }} />
              <div className="flex min-w-0 flex-1 flex-col justify-between bg-keep/85 px-1.5 py-1 text-[10px] font-medium text-background">
                <span className="truncate">{clip.label}</span>
                <span className="h-1 w-6 rounded-full bg-background/30" />
              </div>
              <div className="bg-hatch-cut" style={{ width: `${clip.outro}%` }} />
            </div>
          ))}
        </Track>
        <Track label="A1">
          <div className="flex h-8 flex-1 items-center justify-between rounded-md bg-muted/70 px-2">
            {WAVE.map((height, i) => (
              <span
                key={i}
                className="w-[3px] rounded-full bg-primary/60"
                style={{ height: `${height * 9}%` }}
              />
            ))}
          </div>
        </Track>

        <div className="pointer-events-none absolute inset-y-2 left-14 right-4">
          <div className="animate-playhead absolute inset-y-0 w-px bg-primary shadow-[0_0_12px_var(--primary)]">
            <span className="absolute -top-1 -left-[5px] size-[11px] rotate-45 rounded-[2px] bg-primary" />
          </div>
        </div>
      </div>

      <div className="flex flex-wrap items-center gap-x-4 gap-y-1 border-t px-4 py-2.5 text-[11px] text-muted-foreground">
        <Legend className="bg-keep">Kept</Legend>
        <Legend className="bg-hatch-cut">Intro / outro cut</Legend>
      </div>
    </div>
  );
}

function Track({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="flex items-center gap-2">
      <span className="w-8 shrink-0 font-mono text-[10px] text-muted-foreground">{label}</span>
      <div className="flex min-w-0 flex-1 gap-1">{children}</div>
    </div>
  );
}

function Legend({ className, children }: { className: string; children: React.ReactNode }) {
  return (
    <span className="inline-flex items-center gap-1.5">
      <span className={cn("h-2 w-4 rounded-sm", className)} />
      {children}
    </span>
  );
}
