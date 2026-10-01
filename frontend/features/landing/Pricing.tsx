"use client";

import Link from "next/link";
import { useState } from "react";
import { CheckIcon } from "@/components/icons";
import { Button, buttonVariants } from "@/components/ui/button";
import { useAccount } from "@/features/account/AccountContext";
import { LIFETIME_PLAN, PRO_PLAN, type Plan } from "@/lib/account/plans";
import { errorMessage } from "@/lib/errors";
import { cn } from "@/lib/utils";

/** The two plans. Lifetime can be bought once signed in; Pro is announced. */
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

  return (
    <div className="grid gap-4 md:grid-cols-2">
      <PlanCard plan={LIFETIME_PLAN} featured>
        {owned ? (
          <Link href="/studio" className={cn(buttonVariants({ size: "lg" }), "h-11 w-full text-base")}>
            Open the studio
          </Link>
        ) : (
          <Button
            type="button"
            size="lg"
            className="h-11 w-full text-base"
            disabled={!account || buying}
            onClick={() => void buy()}
          >
            {buying ? "Processing…" : `Buy for ${LIFETIME_PLAN.price}`}
          </Button>
        )}
        {!account && !owned && (
          <p className="text-center text-xs text-muted-foreground">Create an account first.</p>
        )}
        {problem && <p className="text-center text-sm text-destructive">{problem}</p>}
      </PlanCard>
      <PlanCard plan={PRO_PLAN}>
        <Button type="button" size="lg" variant="outline" className="h-11 w-full" disabled>
          Coming soon
        </Button>
      </PlanCard>
    </div>
  );
}

function PlanCard({
  plan,
  featured,
  children,
}: {
  plan: Plan;
  featured?: boolean;
  children: React.ReactNode;
}) {
  return (
    <div
      className={cn(
        "flex flex-col gap-5 rounded-xl p-5",
        featured ? "bg-card ring-2 ring-primary/70" : "bg-card/50 ring-1 ring-border",
      )}
    >
      <div className="flex items-start justify-between gap-3">
        <div>
          <h3 className="font-heading text-lg font-semibold">{plan.name}</h3>
          <p className="text-sm text-muted-foreground">{plan.blurb}</p>
        </div>
        {!plan.available && (
          <span className="shrink-0 rounded-full bg-muted px-2 py-0.5 text-xs text-muted-foreground">
            Later
          </span>
        )}
      </div>
      <p className="flex items-baseline gap-2">
        <span className="font-heading text-4xl font-bold tracking-tight">{plan.price}</span>
        <span className="text-sm text-muted-foreground">{plan.cadence}</span>
      </p>
      <ul className="flex flex-1 flex-col gap-2 text-sm">
        {plan.features.map((feature) => (
          <li key={feature} className="flex gap-2">
            <CheckIcon className={cn("mt-0.5 size-4", featured ? "text-primary" : "text-muted-foreground")} />
            {feature}
          </li>
        ))}
      </ul>
      <div className="flex flex-col gap-2">{children}</div>
    </div>
  );
}
