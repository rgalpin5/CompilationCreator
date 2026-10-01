"use client";

import Link from "next/link";
import { ArrowRightIcon, LockIcon } from "@/components/icons";
import SiteHeader from "@/components/SiteHeader";
import { buttonVariants } from "@/components/ui/button";
import AccountPanel from "@/features/account/AccountPanel";
import { useAccount } from "@/features/account/AccountContext";
import { LIFETIME_PLAN } from "@/lib/account/plans";
import { cn } from "@/lib/utils";
import HeroReel from "./HeroReel";
import Pricing from "./Pricing";

const STEPS = [
  {
    title: "Pick",
    body: "Paste a channel link. Its uploads load as a grid, newest first, with how often you have used each one.",
  },
  {
    title: "Trim",
    body: "Step through every clip in a built-in player. Drag the handles or press Cut here to drop the intro and outro.",
  },
  {
    title: "Export",
    body: "One MP4 in 1080p or 4K. Matching clips are joined without re-encoding, so long compilations finish fast.",
  },
];

const DETAILS = [
  { stat: "100", label: "clips per compilation" },
  { stat: "4 h", label: "of output per export" },
  { stat: "4K", label: "output when you want it" },
];

/** The public front page: what it does, an account, and the purchase. */
export default function Landing() {
  const { owned, account, demo } = useAccount();

  return (
    <div className="flex flex-1 flex-col">
      <SiteHeader
        nav={
          <div className="hidden items-center gap-1 sm:flex">
            <a href="#how" className="rounded-md px-2.5 py-1 text-sm text-muted-foreground hover:text-foreground">
              How it works
            </a>
            <a href="#get-access" className="rounded-md px-2.5 py-1 text-sm text-muted-foreground hover:text-foreground">
              Pricing
            </a>
          </div>
        }
        actions={<StudioLink owned={owned} signedIn={account != null} />}
      />

      <main className="flex flex-1 flex-col">
        <section className="relative overflow-hidden border-b">
          <div className="bg-frame-grid absolute inset-0 [mask-image:radial-gradient(ellipse_at_top,black_30%,transparent_75%)]" />
          <div className="relative mx-auto grid w-full max-w-7xl items-center gap-12 px-4 py-16 md:px-6 md:py-24 lg:grid-cols-[minmax(0,5fr)_minmax(0,6fr)]">
            <div className="flex flex-col gap-6">
              <p className="inline-flex items-center gap-2 self-start rounded-full bg-muted px-3 py-1 font-mono text-xs text-muted-foreground">
                <span className="size-1.5 rounded-full bg-primary" />
                Compilation editor for YouTube channels
              </p>
              <h1 className="font-heading text-4xl leading-[1.05] font-bold tracking-tight text-balance sm:text-5xl lg:text-6xl">
                Cut the intros.
                <br />
                Keep the <span className="text-primary">good part.</span>
              </h1>
              <p className="max-w-xl text-lg text-pretty text-muted-foreground">
                CompCreator turns a channel&apos;s videos into one continuous compilation. Choose the
                uploads, trim each one in seconds, and download a single MP4.
              </p>
              <div className="flex flex-wrap items-center gap-3">
                <a href="#get-access" className={cn(buttonVariants({ size: "lg" }), "h-11 px-5 text-base")}>
                  Get lifetime access · {LIFETIME_PLAN.price}
                </a>
                <a href="#how" className={cn(buttonVariants({ size: "lg", variant: "ghost" }), "h-11 px-4 text-base")}>
                  See how it works
                </a>
              </div>
            </div>
            <HeroReel />
          </div>
        </section>

        <section id="how" className="scroll-mt-14 border-b">
          <div className="mx-auto w-full max-w-7xl px-4 py-16 md:px-6 md:py-20">
            <h2 className="font-heading text-3xl font-bold tracking-tight">Three steps, one file</h2>
            <ol className="mt-10 grid gap-px overflow-hidden rounded-xl bg-border md:grid-cols-3">
              {STEPS.map((step, i) => (
                <li key={step.title} className="flex flex-col gap-3 bg-background p-6">
                  <span className="font-mono text-sm text-primary tabular-nums">0{i + 1}</span>
                  <h3 className="font-heading text-xl font-semibold">{step.title}</h3>
                  <p className="text-sm leading-relaxed text-muted-foreground">{step.body}</p>
                </li>
              ))}
            </ol>
            <dl className="mt-10 grid grid-cols-3 gap-4">
              {DETAILS.map((detail) => (
                <div key={detail.label} className="flex flex-col gap-1 border-l-2 border-keep/60 pl-4">
                  <dt className="order-2 text-sm text-muted-foreground">{detail.label}</dt>
                  <dd className="order-1 font-heading text-3xl font-bold tabular-nums">{detail.stat}</dd>
                </div>
              ))}
            </dl>
          </div>
        </section>

        <section id="get-access" className="scroll-mt-14">
          <div className="mx-auto grid w-full max-w-7xl gap-10 px-4 py-16 md:px-6 md:py-20 lg:grid-cols-[minmax(0,2fr)_minmax(0,3fr)]">
            <div className="flex flex-col gap-6">
              <div>
                <h2 className="font-heading text-3xl font-bold tracking-tight">Get access</h2>
                <p className="mt-2 text-muted-foreground">
                  Make an account, buy once, and the studio unlocks on this account.
                </p>
                {demo && (
                  <p className="mt-3 rounded-lg border border-dashed border-primary/40 px-3 py-2 text-xs text-muted-foreground">
                    <span className="font-medium text-primary">Preview mode.</span> Accounts stay in
                    this browser and no payment is taken.
                  </p>
                )}
              </div>
              <div className="rounded-xl bg-card p-5 ring-1 ring-border">
                <AccountPanel />
              </div>
            </div>
            <div className="flex flex-col gap-4 lg:pt-[4.75rem]">
              <Pricing />
            </div>
          </div>
        </section>
      </main>

      <footer className="border-t">
        <div className="mx-auto flex w-full max-w-7xl flex-col gap-2 px-4 py-6 text-xs text-muted-foreground md:flex-row md:justify-between md:px-6">
          <p>Use CompCreator only with videos you have the rights to use.</p>
          <p>CompCreator</p>
        </div>
      </footer>
    </div>
  );
}

function StudioLink({ owned, signedIn }: { owned: boolean; signedIn: boolean }) {
  if (owned) {
    return (
      <Link href="/studio" className={buttonVariants({ size: "sm" })}>
        Open studio
        <ArrowRightIcon />
      </Link>
    );
  }
  return (
    <a href="#get-access" className={buttonVariants({ size: "sm", variant: "outline" })}>
      <LockIcon />
      {signedIn ? "Unlock studio" : "Sign in"}
    </a>
  );
}
