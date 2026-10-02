import { CheckIcon } from "@/components/icons";
import { cn } from "@/lib/utils";

/** A miniature window frame shared by the three step illustrations. */
function Frame({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div aria-hidden="true" className="overflow-hidden rounded-md bg-background ring-1 ring-border">
      <div className="flex items-center gap-1.5 border-b px-3 py-2">
        <span className="size-1.5 rounded-full bg-muted-foreground/40" />
        <span className="size-1.5 rounded-full bg-muted-foreground/40" />
        <span className="size-1.5 rounded-full bg-muted-foreground/40" />
        <span className="ml-2 truncate font-mono text-2xs text-muted-foreground">{title}</span>
      </div>
      <div className="@container p-3">{children}</div>
    </div>
  );
}

const TILES = [
  { len: "12:04", picked: 1 },
  { len: "08:31", picked: 0 },
  { len: "15:47", picked: 0 },
  { len: "03:12", picked: 2 },
  { len: "21:09", picked: 1 },
  { len: "06:55", picked: 0 },
];

/** Step 1: a channel link, its uploads as a grid, and a few picked. */
export function PickArt() {
  return (
    <Frame title="channel / uploads">
      <div className="mb-3 flex gap-2">
        <span className="flex h-7 min-w-0 flex-1 items-center truncate rounded-sm bg-muted/60 px-2 font-mono text-2xs text-foreground/85 ring-1 ring-border">
          youtube.com/@yourchannel
        </span>
        <span className="flex h-7 shrink-0 items-center rounded-sm bg-primary px-2.5 text-2xs font-semibold text-primary-foreground">
          Load
        </span>
      </div>
      <div className="grid grid-cols-3 gap-2">
        {TILES.map((tile, i) => (
          <div key={i} className="flex flex-col gap-1">
            <div
              className={cn(
                "relative aspect-video rounded-[3px] bg-muted/70",
                tile.picked ? "ring-2 ring-primary" : "ring-1 ring-border",
              )}
            >
              <span className="absolute inset-0 grid place-items-center">
                <span className="size-0 border-y-[5px] border-l-[8px] border-y-transparent border-l-muted-foreground/50" />
              </span>
              <span className="absolute right-1 bottom-1 rounded-[2px] bg-background/80 px-1 font-mono text-2xs leading-3 text-muted-foreground tabular-nums">
                {tile.len}
              </span>
              {tile.picked > 0 && (
                <span className="absolute top-1 left-1 grid size-4 place-items-center rounded-full bg-primary text-primary-foreground">
                  <CheckIcon className="size-2.5" />
                </span>
              )}
            </div>
            <span className="h-1 w-3/4 rounded-full bg-muted-foreground/30" />
          </div>
        ))}
      </div>
    </Frame>
  );
}

/** Step 2: the player above its trim bar, with the intro and outro hatched away. */
export function TrimArt() {
  return (
    <Frame title="trim / rally-12.mp4">
      <div className="relative mb-3 grid aspect-video place-items-center rounded-[3px] bg-muted/70 ring-1 ring-border">
        <span className="size-0 border-y-[9px] border-l-[14px] border-y-transparent border-l-muted-foreground/50" />
        <span className="absolute bottom-1.5 left-2 font-mono text-2xs text-muted-foreground tabular-nums">
          00:00:14 / 00:12:04
        </span>
      </div>
      <div className="relative pt-5">
        <span className="absolute top-0 left-[17%] -translate-x-1/2 font-mono text-2xs text-primary tabular-nums">
          IN<span className="hidden @[17rem]:inline"> 00:00:14</span>
        </span>
        <span className="absolute top-0 left-[79%] -translate-x-1/2 font-mono text-2xs text-primary tabular-nums">
          OUT<span className="hidden @[17rem]:inline"> 00:11:20</span>
        </span>
        <div className="flex h-9 items-stretch overflow-hidden rounded-[3px] ring-1 ring-border">
          <span className="bg-hatch-cut w-[17%]" />
          <span className="w-1 bg-primary" />
          <span className="flex flex-1 items-center gap-[3px] bg-keep px-2">
            {Array.from({ length: 22 }, (_, i) => (
              <span
                key={i}
                className="w-px flex-1 rounded-full bg-background/40"
                style={{ height: `${30 + ((i * 37) % 55)}%` }}
              />
            ))}
          </span>
          <span className="w-1 bg-primary" />
          <span className="bg-hatch-cut w-[21%]" />
        </div>
      </div>
      <div className="mt-3 flex gap-2 font-mono text-2xs">
        <span className="rounded-sm bg-primary px-2 py-1 font-semibold text-primary-foreground">Cut here</span>
        <span className="rounded-sm px-2 py-1 text-muted-foreground ring-1 ring-border">Next clip</span>
      </div>
    </Frame>
  );
}

/** Step 3: trimmed clips ripple into one file with its format and a progress bar. */
export function ExportArt() {
  return (
    <Frame title="export">
      <div className="flex h-9 gap-px overflow-hidden rounded-[3px] ring-1 ring-border">
        {[5, 3, 6, 2, 4].map((grow, i) => (
          <span key={i} className="bg-keep" style={{ flexGrow: grow, flexBasis: 0 }} />
        ))}
      </div>
      <div className="my-2 flex justify-center text-muted-foreground">
        <svg viewBox="0 0 12 12" className="size-3" fill="none" stroke="currentColor" strokeWidth="1.5">
          <path d="M6 1v9M2.5 6.5 6 10l3.5-3.5" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
      </div>
      <div className="rounded-[3px] bg-muted/50 p-3 ring-1 ring-primary/60">
        <div className="flex items-baseline justify-between gap-2">
          <span className="truncate font-mono text-xs font-semibold">compilation.mp4</span>
          <span className="font-mono text-2xs text-muted-foreground tabular-nums">5 clips</span>
        </div>
        <div className="mt-2 flex gap-1.5 font-mono text-2xs">
          <span className="rounded-sm px-1.5 py-0.5 text-muted-foreground ring-1 ring-border">1080p</span>
          <span className="rounded-sm bg-primary px-1.5 py-0.5 font-semibold text-primary-foreground">4K</span>
        </div>
        <div className="mt-3 h-1 overflow-hidden rounded-full bg-muted">
          <span className="block h-full w-full bg-primary" />
        </div>
        <p className="mt-1.5 font-mono text-2xs text-primary">Ready · download MP4</p>
      </div>
    </Frame>
  );
}
