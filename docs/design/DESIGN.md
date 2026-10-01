# CompCreator design system

The system is already in the code. `frontend/app/globals.css` defines every token, and the components in `frontend/components/ui/` and `frontend/features/` use them. This document records what is there and why, and lists the few places that drift. [`design-tokens.json`](design-tokens.json) mirrors the tokens for tools that cannot read CSS, and [`design-preview.html`](design-preview.html) shows them rendered.

## Idea

CompCreator is a small editing tool, so it borrows the look of an editing suite: a dark, cool workspace where the footage is the brightest thing on screen. Three colors carry meaning, and each has one job:

| Role | Token | Why |
|---|---|---|
| Action and selection | `--primary` (mint, `oklch(0.86 0.13 168)`) | It stands apart from the navy and from both footage colors, so a selected clip or a primary button never looks like a timeline segment. |
| Kept footage | `--keep` (sky, `oklch(0.76 0.12 235)`) | It sits close to the surface hue, so long stretches of kept footage stay calm. |
| Cut footage | `--cut` (rose, `oklch(0.7 0.17 15)`), plus the `bg-hatch-cut` hatching | It is the warm opposite of keep. The hatching means cut footage still reads for colour-blind users and in greyscale. |

Every other color is a neutral on the 255° (navy) hue, ordered by lightness. `--cut` and `--destructive` are the same value on purpose, because cutting footage is a destructive edit.

## Color

Surfaces get lighter as they rise: `background` 0.16 → `card` 0.20 → `popover` 0.215 → `muted`/`secondary` 0.25 → `accent` 0.28. Borders are white at 11% alpha (15% for inputs) rather than solid grey, so they stay visible on any of those surfaces.

There is only a dark theme. `:root` and `.dark` share one block and `color-scheme: dark` is set. That is a deliberate choice: video judged on a dark surround looks the way it will when played back. Adding a light theme would mean writing a second token block, not editing components, because nothing outside `globals.css` uses a hardcoded neutral (see the drift list below).

Measured contrast (WCAG 2.x):

| Pair | Ratio |
|---|---|
| foreground / background | 17.3 |
| foreground / card | 16.1 |
| muted-foreground / card | 7.9 |
| muted-foreground / muted | 7.0 |
| primary-foreground / primary | 12.4 |
| destructive / card | 6.3 |
| keep / background | 9.2 |

Every pair clears AA. Most clear AAA.

## Typography

| Family | Token | Used for |
|---|---|---|
| Geist | `font-sans` | All UI text |
| Geist Mono | `font-mono` | Timecodes, durations, counts. Always paired with `tabular-nums` so numbers don't jump while they change. |
| Bricolage Grotesque | `font-heading` | Headings, prices and stats only. It adds personality where the page is mostly quiet. |

The scale in use: `text-sm` (14px) is the default UI size and appears 48 times. `text-xs` covers secondary text, and `text-3xl`–`6xl` with `font-heading` covers the landing page. Display headings use `leading-[1.05] tracking-tight text-balance`.

**Missing step:** `text-[11px]` appears 7 times and `text-[10px]` twice, all for mono timecodes and meta labels. These now use the `text-2xs` token.

## Spacing, radius, elevation

- **Spacing** uses Tailwind's 4px unit. Most values are 2 (8px, used 81 times), 3 and 1, followed by 4 and 6. No arbitrary values appear except one `pt-[4.75rem]` that clears the header.
- **Radius** comes from `--radius: 0.5rem`. Buttons, inputs and thumbnails use `rounded-lg` (8px), cards and panels use `rounded-xl` (~11px), and pills and the playhead use `rounded-full`. Corners are soft but not bubbly, which suits a tool.
- **Elevation** is mostly done with surface lightness and `ring-1 ring-border`, not shadows. The one large shadow is the landing hero reel (`shadow-2xl shadow-black/40`). The primary glow marks the playhead only.

## Motion

Transitions are short and only change color (`transition-colors`). The one decorative animation is the hero playhead sweep (`animate-playhead`, 9s linear). Under `prefers-reduced-motion` it freezes at 38%.

## Texture utilities

- `bg-hatch-cut`: diagonal hatching that marks trimmed footage.
- `bg-frame-grid`: a 48px grid at 5% alpha, like a monitor's safe-area guides, faded with a radial mask behind the hero. It is the only "gradient" in the app, and it has a purpose.

## Drift (fixed)

These were the only places that bypassed the tokens. The badge, `text-2xs` and `shadow-glow` fixes have been applied; the two scrim rows are left as they are on purpose. The `text-[10px]` labels in `HeroReel.tsx` moved up to 11px.

| Where | Issue | Fix |
|---|---|---|
| `frontend/features/logs/VideoTable.tsx:109` | The "Used N×" badge uses `bg-emerald-600` / `bg-teal-700` with `text-white`. White on emerald-600 is **3.77:1** at 12px, which fails AA. The colors are also outside the palette. | Use `bg-primary text-primary-foreground` for the top count and `bg-secondary text-secondary-foreground` for the others. |
| `HeroReel.tsx:19,36,63,74`, `VideoCard.tsx:41`, `CutStep.tsx:129`, `Timeline.tsx:43,90`, `TrimBar.tsx:109` | `text-[11px]` / `text-[10px]` | Add `--text-2xs: 0.6875rem` to `@theme` and use `text-2xs`. |
| `TrimBar.tsx:83`, `HeroReel.tsx:57` | Two different glow sizes: `shadow-[0_0_8px_var(--primary)]` and `shadow-[0_0_12px_…]` | Add `--shadow-glow: 0 0 10px var(--primary)` and use `shadow-glow`. |
| `VideoCard.tsx:41`, `YouTubeSession.tsx:68` | `bg-black/75 text-white` for the duration badge on thumbnails | This is fine, because a scrim over a photo has to be absolute black. Optionally name it `--scrim`. |
| `HeroReel.tsx:32` | `ring-black/30` | Fine, for the same reason. |

Added to `globals.css`:

```css
@theme inline {
  --text-2xs: 0.6875rem;
  --text-2xs--line-height: 1rem;
  --shadow-glow: 0 0 10px var(--primary);
}
```

## Audit

| Dimension | Score | Notes |
|---|---|---|
| Color consistency | 9 | One off-palette badge; no raw hex or oklch values in components. |
| Typography hierarchy | 8 | Clear three-family split. The 10/11px arbitrary sizes need a token. |
| Spacing rhythm | 9 | Tight clusters on the 4px grid. |
| Component consistency | 8 | Buttons and cards come from shadcn (`components/ui/`). The badge drifts. |
| Responsive | 8 | `md`/`lg` grid swaps. The logs table falls back to `min-w-[720px]` with horizontal scroll, which is acceptable for tabular data. |
| Dark mode | 10 | Dark only, on purpose, set once. |
| Animation | 9 | One decorative animation, and it respects reduced motion. |
| Accessibility | 8 | Strong contrast, consistent `focus-visible:ring-3 ring-ring/50`, and hatching backs up color. Minus the badge. |
| Information density | 8 | Dense where it should be (timeline, logs) and spacious on the landing page. |
| Polish | 8 | Hover and focus states are consistent. `transition-all` on buttons is a shadcn default; `transition-[color,background-color,box-shadow]` would be tighter. |

## AI-slop check

The app passes. It has no purple-to-blue gradients, no glass cards and no gradient text. The hero is not centered over a stock gradient: it sits beside a working timeline mock-up. The display font has character, and the accent colors carry domain meaning (keep, cut, act) rather than decoration.
