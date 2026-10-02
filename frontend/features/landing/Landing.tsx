"use client";

import Link from "next/link";
import { ArrowRightIcon, CheckIcon, LockIcon } from "@/components/icons";
import SiteHeader from "@/components/SiteHeader";
import { buttonVariants } from "@/components/ui/button";
import AccountPanel from "@/features/account/AccountPanel";
import { useAccount } from "@/features/account/AccountContext";
import { LIFETIME_PLAN } from "@/lib/account/plans";
import { cn } from "@/lib/utils";
import HeroReel from "./HeroReel";
import HowSequence, { Limits } from "./HowSequence";
import Marker from "./Marker";
import Pricing, { ProRow } from "./Pricing";
import { TC } from "./timeline";
import Transport from "./Transport";

/** The public front page: what it does, an account, and the purchase. */
export default function Landing() {
  const { owned, account, demo } = useAccount();

  return (
    <div id="top" className="flex flex-1 flex-col overflow-x-clip">
      <SiteHeader
        nav={
          <div className="hidden items-center gap-1 sm:flex">
            <a href="#how" className="focus-ring rounded-md px-2.5 py-1 text-sm text-muted-foreground hover:text-foreground">
              How it works
            </a>
            <a href="#get-access" className="focus-ring rounded-md px-2.5 py-1 text-sm text-muted-foreground hover:text-foreground">
              Pricing
            </a>
          </div>
        }
        actions={<StudioLink owned={owned} signedIn={account != null} />}
      />

      <main className="flex flex-1 flex-col">
        <section className="relative border-b">
          <div className="bg-frame-grid absolute inset-0 [mask-image:radial-gradient(ellipse_at_top,black_25%,transparent_75%)]" />
          <div className="relative mx-auto flex w-full max-w-7xl flex-col gap-10 px-4 pt-10 pb-12 md:gap-12 md:px-6 md:pt-16 md:pb-14">
            <div className="flex flex-col gap-8">
              <Marker timecode={TC.intro}>
                <span className="sm:hidden">Compilation editor</span>
                <span className="hidden sm:inline">Compilation editor for YouTube channels</span>
              </Marker>
              <h1 className="font-heading text-[clamp(3rem,13vw,4.75rem)] md:text-[clamp(4.5rem,8.2vw,7.5rem)] leading-[0.9] font-extrabold tracking-[-0.04em] text-balance">
                <span className="rise-in block" style={{ "--delay": "0.05s" } as React.CSSProperties}>
                  Cut the <br className="md:hidden" />
                  <span className="relative inline-block px-[0.06em] text-cut">
                    <span
                      aria-hidden="true"
                      className="bg-hatch-cut absolute inset-x-0 inset-y-[0.14em] -z-10 rounded-[0.08em] opacity-70"
                    />
                    intros.
                    <span
                      aria-hidden="true"
                      className="slash-draw absolute -inset-x-[0.06em] top-[56%] h-[0.055em] rounded-full bg-cut"
                    />
                  </span>
                </span>
                <span className="rise-in block" style={{ "--delay": "0.2s" } as React.CSSProperties}>
                  Keep the <br className="md:hidden" />
                  <span className="relative ml-[0.06em] inline-block px-[0.24em] text-primary">
                    <span
                      aria-hidden="true"
                      className="handles-in absolute inset-x-0 top-[0.08em] -bottom-[0.1em] origin-center rounded-[0.1em] border-y-2 border-primary/60 bg-primary/10"
                    >
                      <span className="absolute inset-y-0 left-0 w-[0.11em] rounded-l-[0.08em] bg-primary" />
                      <span className="absolute inset-y-0 right-0 w-[0.11em] rounded-r-[0.08em] bg-primary" />
                    </span>
                    <span className="relative">good part.</span>
                  </span>
                </span>
              </h1>
            </div>

            <div className="rise-in flex flex-col gap-6 lg:flex-row lg:items-end lg:justify-between" style={{ "--delay": "0.4s" } as React.CSSProperties}>
              <p className="max-w-xl text-lg text-pretty text-muted-foreground md:text-xl">
                CompCreator turns a channel&apos;s videos into one continuous compilation. Choose the
                uploads, trim each one in seconds, and download a single MP4.
              </p>
              <div className="flex flex-wrap items-center gap-x-6 gap-y-4">
                <a href="#get-access" className={cn(buttonVariants({ size: "lg" }), "focus-ring h-12 px-6 text-base")}>
                  Get lifetime access · {LIFETIME_PLAN.price}
                </a>
                <a
                  href="#how"
                  className="focus-ring inline-flex items-center gap-1.5 rounded-sm text-base text-foreground underline decoration-muted-foreground/60 underline-offset-[6px] hover:decoration-primary"
                >
                  See how it works
                  <ArrowRightIcon className="size-4 rotate-90" />
                </a>
              </div>
            </div>

            <div className="rise-in" style={{ "--delay": "0.55s" } as React.CSSProperties}>
              <HeroReel />
            </div>
          </div>
        </section>

        <section id="how" className="relative border-b">
          <div className="mx-auto w-full max-w-7xl px-4 pt-16 pb-12 md:px-6 md:pt-24 md:pb-16">
            <div className="reveal-rise flex flex-col gap-6">
              <Marker timecode={TC.how}>How it works</Marker>
              <h2 className="max-w-4xl font-heading text-[clamp(2.25rem,6.4vw,5.25rem)] leading-[0.95] font-extrabold tracking-[-0.035em]">
                Three steps. <span className="text-muted-foreground">One file.</span>
              </h2>
            </div>

            <div className="mt-10 md:mt-14">
              <HowSequence />
            </div>
          </div>

          <div className="mx-auto w-full max-w-7xl px-4 pb-16 md:px-6 md:pb-24">
            <Limits />
          </div>
        </section>

        <section id="get-access">
          <div className="mx-auto w-full max-w-7xl px-4 py-16 md:px-6 md:py-24">
            <div className="reveal-rise flex flex-col gap-6">
              <Marker timecode={TC.access}>Get access</Marker>
              <h2 className="max-w-4xl font-heading text-[clamp(2.25rem,6.4vw,5.25rem)] leading-[0.95] font-extrabold tracking-[-0.035em]">
                Buy once. <span className="text-primary">Cut forever.</span>
              </h2>
              <p className="max-w-xl text-muted-foreground md:text-lg">
                Make an account, buy once, and the studio unlocks on this account.
              </p>
              {demo && (
                <p className="max-w-xl rounded-sm border border-dashed border-primary/40 px-3 py-2 text-xs text-muted-foreground">
                  <span className="font-medium text-primary">Preview mode.</span> Accounts stay in
                  this browser and no payment is taken.
                </p>
              )}
            </div>

            <Stages signedIn={account != null} owned={owned} />

            <div className="mt-8 grid items-stretch gap-8 lg:grid-cols-[minmax(0,5fr)_minmax(0,7fr)] lg:gap-10">
              <div className="reveal-rise flex flex-col overflow-hidden rounded-md bg-card ring-1 ring-border">
                <div className="flex items-center justify-between border-b px-4 py-2.5 font-mono text-2xs tracking-wider text-muted-foreground uppercase">
                  <h3>Account</h3>
                  <span className="flex items-center gap-1.5">
                    <span className={cn("size-1.5 rounded-full", account ? "bg-primary" : "bg-muted-foreground/50")} />
                    {account ? "Signed in" : "Signed out"}
                  </span>
                </div>
                <div className="flex-1 p-5 [&>div]:min-h-0 [&>div]:gap-5">
                  <AccountPanel />
                </div>
                <dl className="flex flex-col gap-2 border-t bg-muted/20 px-5 py-4 font-mono text-xs">
                  {[
                    { k: "Account", v: account ? account.email : "Signed out", on: account != null },
                    { k: "Plan", v: owned ? LIFETIME_PLAN.name : "None yet", on: owned },
                    { k: "Studio", v: owned ? "Unlocked" : "Locked", on: owned },
                  ].map((row) => (
                    <div key={row.k} className="flex items-baseline gap-3">
                      {/* The dotted leader lives inside the dt: a dl's groups may hold only dt and dd. */}
                      <dt className="flex flex-1 items-baseline gap-3 text-muted-foreground">
                        {row.k}
                        <span aria-hidden="true" className="flex-1 -translate-y-[3px] border-b border-dotted border-muted-foreground/40" />
                      </dt>
                      <dd className={cn("flex min-w-0 items-center gap-1.5 truncate", row.on ? "text-primary" : "text-muted-foreground")}>
                        {row.k === "Studio" && (owned ? <CheckIcon className="size-3.5" /> : <LockIcon className="size-3.5" />)}
                        <span className="truncate">{row.v}</span>
                      </dd>
                    </div>
                  ))}
                </dl>
              </div>
              <div className="reveal-rise flex">
                <Pricing />
              </div>
            </div>

            <div className="reveal-rise mt-8 lg:mt-10">
              <ProRow />
            </div>
          </div>
        </section>
      </main>

      <footer className="border-t pb-11">
        <div className="mx-auto flex w-full max-w-7xl flex-col gap-2 px-4 py-6 font-mono text-xs text-muted-foreground md:flex-row md:justify-between md:px-6">
          <p>Use CompCreator only with videos you have the rights to use.</p>
          <p className="tracking-widest uppercase">CompCreator · End of timeline</p>
        </div>
      </footer>

      <Transport />
    </div>
  );
}

function StudioLink({ owned, signedIn }: { owned: boolean; signedIn: boolean }) {
  if (owned) {
    return (
      <Link href="/studio" className={cn(buttonVariants({ size: "sm" }), "focus-ring")}>
        Open studio
        <ArrowRightIcon />
      </Link>
    );
  }
  return (
    <a href="#get-access" className={cn(buttonVariants({ size: "sm", variant: "outline" }), "focus-ring")}>
      <LockIcon />
      {signedIn ? "Unlock studio" : "Sign in"}
    </a>
  );
}

const STAGES = [
  { n: "01", label: "Account" },
  { n: "02", label: "Buy" },
  { n: "03", label: "Open studio" },
];

/** Where you are in the purchase, drawn as three clips on one track. */
function Stages({ signedIn, owned }: { signedIn: boolean; owned: boolean }) {
  // Done clips are behind you; the current one is mint. Opening the studio is never "done" here,
  // because the moment you go there you leave this page.
  const current = owned ? 2 : signedIn ? 1 : 0;
  return (
    <ol aria-label="Steps to unlock the studio" className="mt-10 grid grid-cols-3 gap-1">
      {STAGES.map((stage, i) => {
        const done = i < current;
        const active = i === current;
        const body = (
          <>
            {/* Keep on its own tint is under 4.5:1 at this size, so done numbers use the foreground. */}
            <span className={cn("font-mono text-2xs tabular-nums", done ? "text-foreground" : active ? "text-primary" : "")}>
              {stage.n}
            </span>
            <span className="flex items-center justify-between gap-2 font-heading text-sm font-semibold sm:text-lg">
              {stage.label}
              {done && <span className="sr-only">(done)</span>}
            </span>
          </>
        );
        const className = cn(
          "flex flex-col gap-1 rounded-sm px-3 py-2.5 ring-1 transition-colors duration-500",
          done && "bg-keep/15 text-foreground ring-keep/50",
          active && "bg-primary/10 text-foreground ring-primary",
          !done && !active && "bg-muted/20 text-muted-foreground ring-border",
        );
        return (
          <li key={stage.n} aria-current={active ? "step" : undefined} className="flex">
            <div className={cn(className, "w-full")}>{body}</div>
          </li>
        );
      })}
    </ol>
  );
}
