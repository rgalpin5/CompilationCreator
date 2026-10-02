"use client";

import Link from "next/link";
import { useState } from "react";
import { ArrowRightIcon, CheckIcon, LockIcon } from "@/components/icons";
import { Button, buttonVariants } from "@/components/ui/button";
import { useAccount } from "@/features/account/AccountContext";
import { LIFETIME_PLAN, PRO_PLAN } from "@/lib/account/plans";
import { errorMessage } from "@/lib/errors";
import { cn } from "@/lib/utils";
import Brackets from "./Brackets";

/** The two plans. Lifetime can be bought once signed in; Pro is an empty track, announced only. */
export default function Pricing() {
  const { account, owned, purchase } = useAccount();
  const [buying, setBuying] = useState(false);
  const [problem, setProblem] = useState<string | null>(null);

  async function buy() {
    setBuying(true);
    setProblem(null);
    try {
      await purchase(LIFETIME_PLAN.id);
    } catch (caught: unknown) {
      setProblem(errorMessage(caught));
    } finally {
      setBuying(false);
    }
  }

  // The render metaphor follows the account: nothing yet, ready, then done.
  const render = owned
    ? { label: "Rendered 100%", width: "100%", tone: "text-primary" }
    : account
      ? { label: "Ready to render", width: "34%", tone: "text-keep" }
      : { label: "Not rendered", width: "0%", tone: "text-muted-foreground" };

  return (
    <div className="flex w-full flex-col">
      <div className="relative flex flex-1 flex-col">
        <Brackets className="border-primary/70" />
        <div className="relative flex flex-1 flex-col overflow-hidden rounded-md bg-card ring-1 ring-primary/60">
          <div className="flex items-center justify-between gap-3 border-b px-4 py-2.5 font-mono text-2xs tracking-wider text-muted-foreground uppercase">
            <span className="truncate">{LIFETIME_PLAN.name.toLowerCase()}.mp4</span>
            <span className={cn("tabular-nums", render.tone)}>{render.label}</span>
          </div>
          <div aria-hidden="true" className="bg-hatch-raw h-1.5">
            <div
              className="h-full bg-primary transition-[width] duration-700 ease-out"
              style={{ width: render.width }}
            />
          </div>

          <div className="flex flex-1 flex-col gap-7 p-5 sm:p-8">
            <div className="grid gap-7 sm:grid-cols-[auto_minmax(0,1fr)] sm:gap-10">
              <div className="flex flex-col items-start gap-2">
                <h3 className="rounded-sm bg-primary/15 px-2 py-0.5 font-mono text-2xs tracking-widest text-primary uppercase">
                  {LIFETIME_PLAN.name}
                </h3>
                <p className="font-heading text-[clamp(4.5rem,12vw,7.5rem)] leading-[0.85] font-extrabold tracking-[-0.05em]">
                  {LIFETIME_PLAN.price}
                </p>
                <p className="font-mono text-xs tracking-wider text-muted-foreground uppercase">
                  {LIFETIME_PLAN.cadence}
                </p>
                <p className="max-w-[15rem] text-sm text-muted-foreground">{LIFETIME_PLAN.blurb}</p>
              </div>

              <ul className="flex flex-col gap-2.5 self-center text-sm">
                {LIFETIME_PLAN.features.map((feature) => (
                  <li key={feature} className="flex gap-2.5">
                    <CheckIcon className="mt-0.5 size-4 shrink-0 text-keep" />
                    {feature}
                  </li>
                ))}
              </ul>
            </div>

            <div className="mt-auto flex flex-col gap-2">
              {owned ? (
                <Link
                  href="/studio"
                  className={cn(buttonVariants({ size: "lg" }), "focus-ring h-12 w-full text-base")}
                >
                  Open the studio
                  <ArrowRightIcon />
                </Link>
              ) : account ? (
                <Button
                  type="button"
                  size="lg"
                  className="focus-ring h-12 w-full text-base"
                  disabled={buying}
                  onClick={() => void buy()}
                >
                  {buying ? "Processing…" : `Buy for ${LIFETIME_PLAN.price}`}
                </Button>
              ) : (
                <Button
                  type="button"
                  size="lg"
                  variant="outline"
                  disabled
                  className="h-12 w-full border-dashed text-base text-muted-foreground disabled:opacity-100"
                >
                  <LockIcon />
                  Create an account to buy
                </Button>
              )}
              {problem && (
                <p role="alert" className="text-center text-sm text-destructive">
                  {problem}
                </p>
              )}
              {/* The buy button turns into a link on success, which drops focus, so say what happened. */}
              <p role="status" className="sr-only">
                {owned ? "Purchase complete. The studio is unlocked." : ""}
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

/** Pro is announced only: an empty track with no price and no button. */
export function ProRow() {
  return (
    <div className="flex flex-col gap-3 rounded-md border border-dashed border-border bg-muted/15 p-4 sm:p-5 lg:flex-row lg:items-center lg:gap-8">
      <div className="flex shrink-0 items-center gap-3">
        <span className="font-mono text-2xs text-muted-foreground">V4</span>
        <h3 className="font-heading text-lg font-semibold">{PRO_PLAN.name}</h3>
        <span className="rounded-sm bg-muted px-1.5 py-0.5 font-mono text-2xs tracking-wider text-muted-foreground uppercase">
          Later
        </span>
      </div>
      <div className="flex min-w-0 flex-1 flex-col gap-1">
        <p className="text-sm text-muted-foreground">{PRO_PLAN.blurb} Not on sale yet.</p>
        <ul className="flex flex-wrap gap-x-4 gap-y-0.5 text-xs text-muted-foreground">
          {PRO_PLAN.features.map((feature) => (
            <li key={feature} className="flex items-center gap-1.5">
              <span aria-hidden="true" className="size-1 rounded-full bg-muted-foreground/60" />
              {feature}
            </li>
          ))}
        </ul>
      </div>
      <span className="shrink-0 font-mono text-xs text-muted-foreground">Price {PRO_PLAN.price}</span>
    </div>
  );
}
